"""The three office buildings used in the campaign."""
from liftsim import Building

BUILDINGS = [
    Building("B1", floors=10, cars=3, rated=13, cap=10, v=1.6, a=1.0, pop_per_floor=50),
    Building("B2", floors=16, cars=4, rated=17, cap=13, v=2.5, a=1.0, pop_per_floor=50),
    Building("B3", floors=24, cars=6, rated=21, cap=16, v=3.5, a=1.2, pop_per_floor=50),
]
