"""Event-driven lift group simulator.

Cars follow directional-collective movement with trapezoidal kinematics, explicit
door and passenger-transfer times, and lobby homing when idle. Four group
controllers are provided:

  NC   nearest car, figure-of-suitability rule, conventional up/down landing calls
  ETA  minimum estimated time of arrival at the landing call
  ETD  ETA plus the delay imposed on passengers already allocated to the car
  ETDQ ETD that knows how many people wait behind each landing call and re-allocates
       the call when its queue grows (occupancy-aware)
  DCS  destination control: each passenger is allocated on registration, with a
       time-to-destination cost, delay to other passengers and a capacity check
  DCSP1, DCSP0  priority-aware destination control: a priority passenger is allocated
       as if general passengers of the same pickup were not there, and general
       passengers who lose their place are re-allocated at once. The delay that a
       priority passenger causes to others has weight 1 (DCSP1) or 0 (DCSP0).

Priority-first boarding (optional) reorders a landing queue so that passengers
flagged for priority board before others; within each group boarding is first come
first served. Nothing else in the controllers uses the priority flag.
"""
from __future__ import annotations
import heapq
import math
import numpy as np

from .model import Building, flight_time_table

UP, DOWN = 1, -1
IDLE, MOVING, OPENING, TRANSFER, CLOSING = 0, 1, 2, 3, 4
INF = float("inf")


def _di(d):
    return 0 if d == UP else 1


class Car:
    __slots__ = ("i", "floor", "dir", "status", "s", "t0", "target", "mver",
                 "onboard", "ndest", "hall", "pick", "serve", "open_t", "door_t",
                 "homing", "lobby_board", "guard_t", "guard_n", "load", "dsize")

    def __init__(self, i, nlev):
        self.i = i
        self.floor = 0
        self.dir = 0
        self.status = IDLE
        self.s = 0
        self.t0 = 0.0
        self.target = 0
        self.mver = 0
        self.onboard = []
        self.ndest = [0] * nlev
        self.dsize = [0] * nlev
        self.load = 0
        self.hall = set()          # conventional landing calls allocated: (floor, dir)
        self.pick = {}             # DCS pickups: (floor, dir) -> list of passenger ids
        self.serve = 0
        self.open_t = 0.0
        self.door_t = 0.0
        self.homing = False
        self.lobby_board = 0
        self.guard_t = -1.0
        self.guard_n = 0


class Sim:
    def __init__(self, b: Building, controller: str, arrivals: dict, t_end: float,
                 priority_share: float = 0.0, priority_boarding: bool = False,
                 homing: bool = True, log_trips: bool = False, debug: bool = False,
                 pri_size: int = 1, pri_tp_factor: float = 1.0, theta: float = 1.0):
        if controller not in ("NC", "ETA", "ETD", "ETDQ", "DCS", "DCSP1", "DCSP0", "DCSPA"):
            raise ValueError(controller)
        self.b = b
        self.ctrl = controller
        self.dcs = controller in ("DCS", "DCSP1", "DCSP0", "DCSPA")
        self.dcsp = controller in ("DCSP1", "DCSP0", "DCSPA")
        self.adaptive = controller == "DCSPA"
        self.theta = theta
        self.nwait = 0
        self.dcsp_alpha = 0.0 if controller == "DCSP0" else 1.0
        self.etdq = controller == "ETDQ"
        self.t_end = float(t_end)
        self.homing = homing
        self.prio_board = priority_boarding
        self.tf, self.ds = flight_time_table(b)
        self.nlev = b.floors + 1
        self.cap = b.cap
        A = arrivals
        self.at = A["t"].astype(float)
        self.ao = A["o"].astype(int).tolist()
        self.ad = A["d"].astype(int).tolist()
        self.pri = (A["u"] < priority_share).tolist()
        self.atl = self.at.tolist()
        self.size = [pri_size if q else 1 for q in self.pri]
        self.tpp = [b.t_p * pri_tp_factor if q else b.t_p for q in self.pri]
        n = len(self.atl)
        self.board_t = [math.nan] * n
        self.alight_t = [math.nan] * n
        self.pcar = [-1] * n                     # DCS allocation
        self.queue = [[[], []] for _ in range(self.nlev)]
        self.reg = [[False, False] for _ in range(self.nlev)]
        self.asg = [[-1, -1] for _ in range(self.nlev)]
        self.unassigned = set()
        self.cars = [Car(i, self.nlev) for i in range(b.cars)]
        self.heap = []
        self.seq = 0
        self.now = 0.0
        self.log_trips = log_trips
        self.trips = []                          # (car, depart time, boarded at lobby)
        self.n_alloc = 0
        self.debug = debug
        self.blog = []                           # debug: (time, car, floor, dir, pid, load_after)
        self.pos_log = []                        # debug: (time, car, floor, event)

    # ------------------------------------------------------------------ events
    def _push(self, t, kind, car, ver=0):
        self.seq += 1
        heapq.heappush(self.heap, (t, self.seq, kind, car, ver))

    def run(self):
        at = self.atl
        n = len(at)
        k = 0
        heap = self.heap
        while True:
            ta = at[k] if k < n else INF
            te = heap[0][0] if heap else INF
            t = ta if ta <= te else te
            if t > self.t_end:
                break
            self.now = t
            if ta <= te:
                self._on_arrival(k)
                k += 1
                continue
            _, _, kind, ci, ver = heapq.heappop(heap)
            c = self.cars[ci]
            if kind == 0:
                if ver == c.mver and c.status == MOVING:
                    self._on_car_arrive(c)
            elif kind == 1:
                self._on_doors_open(c)
            elif kind == 2:
                self._on_transfer_end(c)
            elif kind == 3:
                self._on_doors_closed(c)
        return self

    # ------------------------------------------------------------- arrivals
    def _on_arrival(self, i):
        f, g = self.ao[i], self.ad[i]
        d = UP if g > f else DOWN
        self.queue[f][_di(d)].append(i)
        self.nwait += 1
        if self.dcs:
            c, load_x = self._alloc_dcs(i)
            self._give_pickup(i, c)
            if self.dcsp and self.pri[i] and load_x is not None and load_x > self.cap:
                self._bump_general(c, f, d, load_x - self.cap)
            return
        for c in self.cars:
            if (c.status == TRANSFER and c.floor == f and c.serve == d
                    and c.load + self.size[i] <= self.cap):
                return                                    # boards at end of this transfer
        if not self.reg[f][_di(d)]:
            self.reg[f][_di(d)] = True
            self._assign_call(f, d)
        elif self.etdq:
            ci = self.asg[f][_di(d)]
            if ci >= 0:
                old = self.cars[ci]
                if not (old.floor == f and old.status in (OPENING, TRANSFER, CLOSING)):
                    old.hall.discard((f, d))
                    self.asg[f][_di(d)] = -1
                    self._assign_call(f, d)
                    if self.asg[f][_di(d)] != ci:
                        self._notify(old)

    def _bump_general(self, c, f, d, excess):
        """DCSP: move the last-arrived general passengers of this pickup to other cars now."""
        L = c.pick.get((f, d), [])
        gens = [p for p in L if not self.pri[p]]
        out = []
        while gens and excess > 0:
            p = gens.pop()
            out.append(p)
            excess -= self.size[p]
        if not out:
            return
        o = set(out)
        rest = [p for p in L if p not in o]
        if rest:
            c.pick[(f, d)] = rest
        else:
            c.pick.pop((f, d), None)
        self._reallocate_dcs(out[::-1], exclude=c.i)

    # ------------------------------------------------- conventional landing calls
    def _assign_call(self, f, d, exclude=-1):
        best, bestc = None, INF
        for c in self.cars:
            if c.i == exclude or c.load >= self.cap:
                continue
            cost = self._cost_conventional(c, f, d)
            if cost < bestc - 1e-9:
                best, bestc = c, cost
        if best is None:
            self.asg[f][_di(d)] = -1
            self.unassigned.add((f, d))
            return
        self.n_alloc += 1
        self.unassigned.discard((f, d))
        self.asg[f][_di(d)] = best.i
        best.hall.add((f, d))
        self._notify(best)

    def _clear_call(self, f, d, by_car):
        k = _di(d)
        self.reg[f][k] = False
        self.unassigned.discard((f, d))
        ci = self.asg[f][k]
        self.asg[f][k] = -1
        if ci >= 0:
            c = self.cars[ci]
            c.hall.discard((f, d))
            if c is not by_car:
                self._notify(c)

    def _release_all(self, c):
        calls = list(c.hall)
        c.hall.clear()
        for (f, d) in calls:
            self.asg[f][_di(d)] = -1
        for (f, d) in calls:
            if self.reg[f][_di(d)] and self.queue[f][_di(d)]:
                self._assign_call(f, d, exclude=c.i)
            else:
                self.reg[f][_di(d)] = False

    def _ensure_calls(self, f):
        for d in (UP, DOWN):
            k = _di(d)
            if self.queue[f][k] and not self.reg[f][k]:
                self.reg[f][k] = True
                self._assign_call(f, d)

    def _retry_unassigned(self):
        for (f, d) in sorted(self.unassigned):
            if self.queue[f][_di(d)]:
                self._assign_call(f, d)
            else:
                self.unassigned.discard((f, d))
                self.reg[f][_di(d)] = False

    # -------------------------------------------------------------- DCS
    def _give_pickup(self, i, c):
        f, g = self.ao[i], self.ad[i]
        d = UP if g > f else DOWN
        self.pcar[i] = c.i
        c.pick.setdefault((f, d), []).append(i)
        self.n_alloc += 1
        if not (c.status == TRANSFER and c.floor == f and c.serve == d):
            self._notify(c)

    def _reallocate_dcs(self, ids, exclude):
        for i in ids:
            c, _ = self._alloc_dcs(i, exclude)
            self._give_pickup(i, c)

    # ------------------------------------------------------------ car logic
    def _notify(self, c):
        if c.status == IDLE:
            self._next_action(c)
        elif c.status == MOVING:
            self._reroute(c)

    def _target_floors(self, c):
        fl = [f for f in range(self.nlev) if c.ndest[f]]
        fl += [f for (f, _) in c.hall]
        fl += [f for (f, _), L in c.pick.items() if L]
        return fl

    def _has_call(self, c, f, d):
        if self.dcs:
            L = c.pick.get((f, d))
            return bool(L)
        return (f, d) in c.hall

    def _any_ahead(self, c, x, d):
        for f in self._target_floors(c):
            if (f - x) * d > 0:
                return True
        return False

    def _waiting_for(self, c, x, d):
        q = self.queue[x][_di(d)]
        if not q:
            return False
        if self.dcs:
            return bool(c.pick.get((x, d)))
        return True

    def _any_fit(self, c, x, d):
        free = self.cap - c.load
        if free <= 0:
            return False
        cand = c.pick.get((x, d), ()) if self.dcs else self.queue[x][_di(d)]
        if not cand:
            return True
        size = self.size
        for p in cand:
            if size[p] <= free:
                return True
        return False

    def _handover(self, c, f, d):
        """Conventional calls: car c cannot take anyone of this queue; give the call away."""
        if (f, d) in c.hall:
            c.hall.discard((f, d))
            self.asg[f][_di(d)] = -1
            if self.queue[f][_di(d)]:
                self._assign_call(f, d, exclude=c.i)
            else:
                self.reg[f][_di(d)] = False

    def _service_dir(self, c, x):
        d = c.dir
        if d != 0:
            if self._any_ahead(c, x, d):
                return d
            # nothing further ahead: serve a call at this floor before turning round
            for cand in (d, -d):
                if self._has_call(c, x, cand):
                    return cand
            if self._any_ahead(c, x, -d):
                return -d
            for cand in (d, -d):
                if self._waiting_for(c, x, cand):
                    return cand
            return 0
        for cand in (UP, DOWN):
            if self._waiting_for(c, x, cand) or self._has_call(c, x, cand):
                return cand
        tf = self._target_floors(c)
        if tf:
            f0 = min(tf, key=lambda f: (abs(f - x), f))
            return UP if f0 > x else DOWN
        return 0

    def _choose_next(self, c):
        x, d = c.floor, c.dir
        tfl = self._target_floors(c)
        if not tfl:
            return 0, None
        if d == 0:
            f0 = min(tfl, key=lambda f: (abs(f - x), f))
            if f0 == x:
                others = [f for f in tfl if f != x]
                if not others:
                    return 0, None
                f0 = min(others, key=lambda f: (abs(f - x), f))
            d = UP if f0 > x else DOWN
        for _ in range(2):
            ahead = [f for f in tfl if (f - x) * d > 0]
            if ahead:
                far = max(ahead, key=lambda f: (f - x) * d)
                elig = [f for f in ahead if c.ndest[f] or self._has_call(c, f, d)]
                elig.append(far)
                n = min(elig, key=lambda f: (f - x) * d)
                return d, n
            d = -d
        return 0, None

    def _start_move(self, c, d, n):
        c.status = MOVING
        c.dir = d
        c.s = c.floor
        c.t0 = self.now
        c.target = n
        c.mver += 1
        if self.log_trips and c.floor == 0:
            self.trips.append((c.i, self.now, c.lobby_board))
        c.lobby_board = 0
        self._push(self.now + self.tf[abs(n - c.floor)], 0, c.i, c.mver)

    def _next_action(self, c):
        """Car stationary at c.floor with doors closed."""
        x = c.floor
        sd = self._service_dir(c, x)
        if sd != 0 and self._has_call(c, x, sd):
            room = self._any_fit(c, x, sd)
            if not room and not self.dcs:
                self._handover(c, x, sd)
            if room:
                if c.guard_t == self.now:
                    c.guard_n += 1
                    if c.guard_n > 50:
                        raise RuntimeError("door reopen loop")
                else:
                    c.guard_t, c.guard_n = self.now, 0
                self._open(c, sd)
                return
        d, n = self._choose_next(c)
        if n is None:
            if self.homing and x != 0:
                c.homing = True
                self._start_move(c, DOWN, 0)
                return
            c.status = IDLE
            c.dir = 0
            c.homing = False
            return
        c.homing = False
        self._start_move(c, d, n)

    def _advanced_floor(self, c):
        s, d, n = c.s, c.dir, c.target
        el = self.now - c.t0
        f = s + d
        while f != n:
            if el <= self.ds[abs(f - s)]:
                return f
            f += d
        return n

    def _reroute(self, c):
        a = self._advanced_floor(c)
        d = c.dir
        tfl = self._target_floors(c)
        ahead = [f for f in tfl if (f - a) * d >= 0]
        if ahead:
            far = max(ahead, key=lambda f: (f - a) * d)
            elig = [f for f in ahead if c.ndest[f] or self._has_call(c, f, d)]
            elig.append(far)
            n2 = min(elig, key=lambda f: (f - a) * d)
            c.homing = False
        elif not tfl and self.homing and (0 - a) * d >= 0:
            n2 = 0
            c.homing = True
        else:
            n2 = a
        if n2 != c.target:
            c.target = n2
            c.mver += 1
            self._push(c.t0 + self.tf[abs(n2 - c.s)], 0, c.i, c.mver)

    def _on_car_arrive(self, c):
        n = c.target
        c.floor = n
        c.status = IDLE
        if self.debug:
            self.pos_log.append((self.now, c.i, n, "arrive"))
        if c.homing and n == 0:
            c.homing = False
        sd = self._service_dir(c, n)
        room = sd != 0 and self._any_fit(c, n, sd)
        alight = c.ndest[n] > 0
        board = sd != 0 and room and self._waiting_for(c, n, sd)
        if alight or board or (sd != 0 and room and self._has_call(c, n, sd)):
            self._open(c, sd if sd != 0 else c.dir)
        else:
            self._next_action(c)

    def _open(self, c, sd):
        c.status = OPENING
        c.serve = sd
        if sd != 0:
            c.dir = sd
        c.open_t = self.now
        c.door_t = self.now + self.b.t_open
        self._push(c.door_t, 1, c.i)

    def _board(self, c, x, sd, t_start):
        """Board waiting passengers; returns (number boarded, total transfer time)."""
        if sd == 0:
            return 0, 0.0
        q = self.queue[x][_di(sd)]
        if not q:
            if not self.dcs and self.reg[x][_di(sd)]:
                self._clear_call(x, sd, c)
            return 0, 0.0
        if self.dcs:
            cand = c.pick.get((x, sd), [])
        else:
            cand = q
        if self.prio_board:
            pri = self.pri
            at = self.atl
            cand = sorted(cand, key=lambda p: (not pri[p], at[p], p))
        elif self.dcs:
            # first come, first served means arrival order, also for passengers who were
            # re-allocated to this car after being left behind by another one
            at = self.atl
            cand = sorted(cand, key=lambda p: (at[p], p))
        size = self.size
        free = self.cap - c.load
        take = []
        for p in cand:
            if free <= 0:
                break
            if size[p] <= free:
                take.append(p)
                free -= size[p]
        if not take:
            if not self.dcs:
                self._handover(c, x, sd)
            return 0, 0.0
        tk = set(take)
        tsum = 0.0
        for p in take:
            self.board_t[p] = max(self.atl[p], c.open_t)
            c.onboard.append(p)
            self.nwait -= 1
            c.load += size[p]
            g = self.ad[p]
            c.ndest[g] += 1
            c.dsize[g] += size[p]
            tsum += self.tpp[p]
            self.pcar[p] = c.i if not self.dcs else self.pcar[p]
            if self.debug:
                self.blog.append((self.now, c.i, x, sd, p, c.load))
        self.queue[x][_di(sd)] = [p for p in q if p not in tk]
        if self.dcs:
            rest = [p for p in c.pick.get((x, sd), []) if p not in tk]
            if rest:
                c.pick[(x, sd)] = rest
            else:
                c.pick.pop((x, sd), None)
        else:
            rq = self.queue[x][_di(sd)]
            if not rq:
                self._clear_call(x, sd, c)
            if c.load >= self.cap:
                self._release_all(c)
            elif rq and not self._any_fit(c, x, sd):
                self._handover(c, x, sd)
        return len(take), tsum

    def _on_doors_open(self, c):
        x = c.floor
        t = self.now
        out = [p for p in c.onboard if self.ad[p] == x]
        if self.debug:
            self.pos_log.append((self.now, c.i, x, "open"))
        tout = 0.0
        for p in out:
            tout += self.tpp[p]
            self.alight_t[p] = t + tout
            c.load -= self.size[p]
        if out:
            c.onboard = [p for p in c.onboard if self.ad[p] != x]
            c.ndest[x] = 0
            c.dsize[x] = 0
        sd = self._service_dir(c, x)
        if sd == 0:
            sd = c.serve
        c.serve = sd
        if sd != 0:
            c.dir = sd
        nb, tin = self._board(c, x, sd, t + tout)
        if x == 0:
            c.lobby_board += nb
        c.status = TRANSFER
        c.door_t = t + tout + tin
        self._push(c.door_t, 2, c.i)

    def _on_transfer_end(self, c):
        x, sd = c.floor, c.serve
        nb = 0
        if sd != 0 and self._waiting_for(c, x, sd) and self._any_fit(c, x, sd):
            nb, tin = self._board(c, x, sd, self.now)
        if nb:
            if x == 0:
                c.lobby_board += nb
            c.door_t = self.now + tin
            self._push(c.door_t, 2, c.i)
            return
        c.status = CLOSING
        c.door_t = self.now + self.b.t_close
        self._push(c.door_t, 3, c.i)

    def _on_doors_closed(self, c):
        c.status = IDLE
        x = c.floor
        if self.dcs:
            free = self.cap - c.load
            stuck = []
            for d in (UP, DOWN):
                L = c.pick.get((x, d))
                if not L:
                    continue
                if free <= 0:
                    stuck += L
                    c.pick.pop((x, d), None)
                elif d == c.serve and not self._any_fit(c, x, d):
                    stuck += L
                    c.pick.pop((x, d), None)
            if stuck:
                self._reallocate_dcs(stuck, exclude=c.i)
        else:
            self._ensure_calls(x)
            if self.unassigned:
                self._retry_unassigned()
        if c.status == IDLE:
            self._next_action(c)

    # ------------------------------------------------------------ planning
    def _plan(self, c, extra=None):
        """Estimate the time at which car c reaches each of its stops.

        Items: ('c', f) car calls (weight = passengers alighting), ('h', f, d) landing
        calls or DCS pickups (weight = expected boarders), ('d', key, f) drops of DCS
        passengers not yet on board (activated when their pickup is served).
        extra: optional (f, d, w, dropdict) describing one additional landing stop.
        Returns (visit_times, weights, load_at_extra).
        """
        b = self.b
        tf = self.tf
        stops = {}       # floor -> list of [kind, key, weight, dir, places]
        weights = {}
        later = {}       # pickup key -> list of (floor, weight, key, places)
        size = self.size
        for f in range(self.nlev):
            if c.ndest[f]:
                k = ("c", f)
                stops.setdefault(f, []).append(["c", k, c.ndest[f], 0, c.dsize[f]])
                weights[k] = c.ndest[f]
        if self.dcs:
            for (f, d), L in c.pick.items():
                if not L:
                    continue
                k = ("h", f, d)
                stops.setdefault(f, []).append(["h", k, len(L), d, sum(size[p] for p in L)])
                weights[k] = len(L)
                dd = {}
                ds = {}
                for p in L:
                    g = self.ad[p]
                    dd[g] = dd.get(g, 0) + 1
                    ds[g] = ds.get(g, 0) + size[p]
                later[k] = [(g, w, ("d", k, g), ds[g]) for g, w in dd.items()]
                for g, w in dd.items():
                    weights[("d", k, g)] = w
        else:
            for (f, d) in c.hall:
                k = ("h", f, d)
                if self.etdq:
                    q = self.queue[f][_di(d)]
                    w = max(1, len(q))
                    sz = max(1, sum(size[p] for p in q))
                else:
                    w = sz = 1
                stops.setdefault(f, []).append(["h", k, w, d, sz])
                weights[k] = w
        xkey = None
        if extra is not None:
            f, d, w, dd, xs = extra
            xkey = ("x", f, d)
            stops.setdefault(f, []).append(["h", xkey, w, d, xs])
            if dd:
                later[xkey] = [(g, ww, ("xd", g), xs) for g, ww in dd.items()]
        load = c.load
        load_x = None
        visit = {}
        # initial state
        first = None
        if c.status == MOVING:
            a = self._advanced_floor(c)
            pos, time, d = a, None, c.dir
            first = (c.s, c.t0)
            allow = True
        elif c.status == IDLE:
            pos, time, d = c.floor, self.now, c.dir
            allow = True
        else:
            pos, d = c.floor, c.serve
            if c.status == OPENING:
                est = c.ndest[pos] + len(self.queue[pos][_di(d)]) if d else c.ndest[pos]
                tfree = c.door_t + est * b.t_p + b.t_close
            elif c.status == TRANSFER:
                tfree = c.door_t + b.t_close
            else:
                tfree = c.door_t
            time = tfree
            # items at this floor in the serving direction board in the current dwell
            if d != 0 and pos in stops:
                keep = []
                for it in stops[pos]:
                    if it[0] == "h" and it[3] == d and c.status != CLOSING:
                        visit[it[1]] = self.now
                        load += it[4]
                        if it[1] == xkey:
                            load_x = load
                        for (g, w, kk, zz) in later.get(it[1], []):
                            stops.setdefault(g, []).append(["c", kk, w, 0, zz])
                    else:
                        keep.append(it)
                if keep:
                    stops[pos] = keep
                else:
                    del stops[pos]
            allow = c.status == CLOSING
        loops = 0
        while stops and loops < 8:
            if d == 0:
                f0 = min(stops, key=lambda f: (abs(f - pos), f))
                if f0 == pos:
                    hs = [it[3] for it in stops[pos] if it[0] == "h"]
                    d = hs[0] if hs else UP
                else:
                    d = UP if f0 > pos else DOWN
            ahead = [f for f in stops if (f - pos) * d > 0 or (allow and f == pos)]
            if not ahead:
                if first is not None:
                    time = first[1] + tf[abs(pos - first[0])]
                    first = None
                d = -d
                allow = True
                loops += 1
                continue
            far = max(ahead, key=lambda f: (f - pos) * d)
            elig = [f for f in ahead
                    if any(it[0] == "c" or it[3] == d for it in stops[f])]
            if far not in elig:
                elig.append(far)
            nf = min(elig, key=lambda f: (f - pos) * d)
            if first is not None:
                time = first[1] + tf[abs(nf - first[0])]
                first = None
            elif nf != pos:
                time += tf[abs(nf - pos)]
            items = stops.pop(nf)
            served = 0
            keep = []
            for it in items:
                if it[0] == "c":
                    visit[it[1]] = time
                    served += it[2]
                    load -= it[4]
            for it in items:
                if it[0] == "h" and it[3] == d:
                    visit[it[1]] = time
                    served += it[2]
                    load += it[4]
                    if it[1] == xkey:
                        load_x = load
                    for (g, w, kk, zz) in later.get(it[1], []):
                        stops.setdefault(g, []).append(["c", kk, w, 0, zz])
                elif it[0] == "h":
                    keep.append(it)
            beyond = any((f - nf) * d > 0 for f in stops)
            reverse = False
            if keep and not beyond:
                for it in keep:
                    visit[it[1]] = time
                    served += it[2]
                    load += it[4]
                    if it[1] == xkey:
                        load_x = load
                    for (g, w, kk, zz) in later.get(it[1], []):
                        stops.setdefault(g, []).append(["c", kk, w, 0, zz])
                keep = []
                reverse = True
            if keep:
                stops[nf] = keep
            time += b.t_open + b.t_close + b.t_p * served
            pos = nf
            allow = False
            if reverse or not any((f - nf) * d > 0 for f in stops):
                d = -d
                allow = reverse is False and nf in stops
        return visit, weights, load_x

    # ------------------------------------------------------------ controllers
    def _nc_position(self, c):
        if c.status == MOVING:
            return self._advanced_floor(c), c.dir
        if c.status == IDLE:
            return c.floor, (c.dir if self._target_floors(c) else 0)
        return c.floor, c.serve

    def _cost_conventional(self, c, f, d):
        if self.ctrl == "NC":
            N = self.b.floors
            p, cd = self._nc_position(c)
            dist = abs(f - p)
            if cd == 0:
                fs = N + 1 - dist
            elif (f - p) * cd > 0 or f == p:
                fs = N + 2 - dist if d == cd else N + 1 - dist
            else:
                fs = 1
            return -fs + 1e-6 * c.i
        base, w, _ = self._plan(c)
        if self.etdq:
            q = self.queue[f][_di(d)]
            xw = max(1, len(q))
            xs = max(1, sum(self.size[p] for p in q))
        else:
            xw = xs = 1
        new, _, load_x = self._plan(c, (f, d, xw, None, xs))
        eta = new.get(("x", f, d), self.now + 1e4) - self.now
        if self.ctrl == "ETA":
            return eta + 1e-6 * c.i
        delay = 0.0
        for k, t0 in base.items():
            t1 = new.get(k, t0)
            if t1 > t0:
                delay += w[k] * (t1 - t0)
        if self.etdq:
            over = 0 if load_x is None else max(0, load_x - self.cap)
            return xw * eta + delay + 30.0 * over + 1e-6 * c.i
        return eta + delay + 1e-6 * c.i

    def _alloc_dcs(self, i, exclude=-1):
        f, g = self.ao[i], self.ad[i]
        d = UP if g > f else DOWN
        best, bestc, bestload = None, INF, None
        sz = self.size[i]
        prio = self.dcsp and self.pri[i]
        for c in self.cars:
            if c.i == exclude and len(self.cars) > 1:
                continue
            base, w, _ = self._plan(c)
            new, _, load_x = self._plan(c, (f, d, 1, {g: 1}, sz))
            tp = new.get(("x", f, d), self.now + 1e4)
            tdrop = new.get(("xd", g), tp + 1e4)
            cost = tdrop - self.now
            if not prio:
                alpha = 1.0
            elif self.adaptive:
                # exploratory extension: strong priority only while the number of people
                # waiting in the building is below theta x total boarding capacity
                alpha = 0.0 if self.nwait <= self.theta * self.cap * len(self.cars) else 1.0
            else:
                alpha = self.dcsp_alpha
            if alpha:
                for k, t0 in base.items():
                    t1 = new.get(k, t0)
                    if t1 > t0:
                        cost += alpha * w[k] * (t1 - t0)
            eff = load_x
            if prio and load_x is not None:
                # general passengers of the same pickup board after this passenger
                eff = load_x - sum(self.size[p] for p in c.pick.get((f, d), ())
                                   if not self.pri[p])
            if eff is None or eff > self.cap:
                cost += 600.0
            cost += 1e-6 * c.i
            if cost < bestc:
                best, bestc, bestload = c, cost, load_x
        return best, bestload

    # ------------------------------------------------------------ outputs
    def passenger_table(self):
        return {
            "t": self.at,
            "o": np.asarray(self.ao),
            "d": np.asarray(self.ad),
            "pri": np.asarray(self.pri, bool),
            "board": np.asarray(self.board_t, float),
            "alight": np.asarray(self.alight_t, float),
            "car": np.asarray(self.pcar, int),
        }
