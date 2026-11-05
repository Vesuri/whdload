"""Exact movement accounting for a future contact-event integrator.

The caller owns event selection and response. A direction is a signed Q14
world vector, normally the forward row of a native rotation matrix. Rounding
occurs on accumulated world displacement, never independently per interval.
Collision corrections neither consume time nor replenish forward distance.
This does not integrate gravity or establish a physical contact law.
"""
from fractions import Fraction as F

class MotionBudget:
    def __init__(self, distance):
        if type(distance) is not int or not 0 <= distance <= 32767:
            raise ValueError("Expected a nonnegative native signed-word distance")
        self.distance = distance
        self.cursor = F(0)
        self.exact_world = [F(0)] * 3
        self.world = [0] * 3
        self.correction = [0] * 3
        self.spans = []
        self.corrections = []

    def advance(self, end, direction):
        if type(end) not in (int, F):
            raise TypeError("Use exact rational event times")
        end = F(end)
        if not self.cursor < end <= 1:
            raise ValueError("Event time must advance within the remaining step")
        direction = tuple(direction)
        if len(direction) != 3 or any(type(x) is not int or not -32768 <= x <= 32767 for x in direction):
            raise ValueError("Expected three signed-word Q14 direction components")
        distance = (end - self.cursor) * self.distance
        exact = [a + distance * d / 16384 for a, d in zip(self.exact_world, direction)]
        rounded = [int(a // 1) for a in exact]
        span = dict(start=self.cursor, end=end, distance=distance,
                    direction=direction, movement=tuple(b-a for a,b in zip(self.world,rounded)))
        self.cursor = end
        self.exact_world = exact
        self.world = rounded
        self.spans.append(span)
        return span

    def push(self, displacement):
        displacement = tuple(displacement)
        if len(displacement) != 3 or any(type(x) is not int for x in displacement):
            raise ValueError("Collision correction must be three explicit integer coordinates")
        self.correction = [a+b for a,b in zip(self.correction,displacement)]
        self.corrections.append(dict(time=self.cursor, displacement=displacement))

    @property
    def remaining_distance(self):
        return (1-self.cursor)*self.distance

    @property
    def displacement(self):
        return tuple(a+b for a,b in zip(self.world,self.correction))

    @property
    def remainder(self):
        return tuple(a-b for a,b in zip(self.exact_world,self.world))
