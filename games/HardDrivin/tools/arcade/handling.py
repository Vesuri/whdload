"""Two-wheel car model for the Amiga, in floats (plan step E2).

The arcade's lateral model (ARCADE_ROMS.md, "MSP vehicle model") with its own
parameters, simplified where the Amiga allows:
- the forward speed u is an input; on the Amiga it comes from the native engine;
- load transfer (LOAD): 'pitch' keeps the arcade's pitch on the springs and
  dampers (two states); 'lag' is a first-order lag on the quasi-static
  ΔN = Fx·h/L with time constant P['tau']; 'static' is ΔN itself;
- no heave, roll or bump stops.
Kept from the arcade's tire ($710D30):
- the Fiala curve with the friction circle;
- the lateral spring and relaxation length, which give the kinematic turn at
  low speed without a mode switch, and the switch to the steady curve when the
  lag would be faster than the step;
- wheel speeds once a torque exceeds μN·r: the sliding tire pushes with the
  whole μN against its slip velocity (u − ωr, v), and the wheel's own torque
  balance uses the whole μN·r. So a wheel that starts to lock under braking
  first gives more lateral force, not less: that is the arcade's turn-in when
  braking in a corner, and how full braking ends with the front locked.

Units are the arcade model's: feet, pounds, slugs, radians, seconds. Body axes:
x forward, y right; yaw rate r and steering angle δ positive to the right.
"""
import math

G = 32.2
P = {
    'W': 3525.0,                # weight, lb
    'I': 2000.0,                # yaw inertia, slug ft²
    'a': 5.0, 'b': 5.0,         # CG to front / rear axle, ft
    'h': 1.567,                 # CG height above the tire forces, ft
    'C': (32000.0, 64000.0),    # cornering stiffness at the static load, lb/rad
    'mu': (1.2, 1.3),
    'k': 8160.0, 'c': 400.0,    # tire lateral spring (lb/ft) and damper (lb s/ft)
    'Iw': 10.0,                 # wheel inertia per axle, slug ft² (tire radius 1 ft)
    'delta_max': 0.6109,        # road wheel angle at full lock, rad (35°)
    'brake_max': 4653.0,        # front brake torque at full pedal, lb ft
    'Ip': 2000.0,               # pitch inertia, slug ft²
    'ks': (3000.0, 3500.0),     # springs, lb/ft
    'cs': (400.0, 500.0),       # dampers, lb s/ft
    'tau': 0.1,                 # LOAD = 'lag': time constant, s
}
# range guards, shared with handling_fx.py; they only act in runaway cases
FX_MAX = 8000.0      # lb, tires' total longitudinal force input
R_MAX = 12.0         # rad/s (the arcade calls more than 10 a crash)
V_MAX = 256.0        # ft/s, lateral velocity
Y_MAX = 4.0          # ft, tire deflection
SLIP_MAX = 128.0     # ft/s, |u − ωr| of a sliding wheel (the arcade's drivetrain
                     # holds a spinning wheel near 100 ft/s in first gear)


def clamp(x, lim):
    return max(-lim, min(lim, x))


def brake_fade(w):
    """$723900's brake torque factor s(ω) for wheel speed w (rad/s at r = 1 ft):
    0 below 2, 0.05·ω up to 10, then ±1; it has ω's sign."""
    a = abs(w)
    s = 0.0 if a < 2 else (0.05 * a if a < 10 else 1.0)
    return math.copysign(s, w)


class Axle:
    """One axle's tire and wheel: lateral deflection y, wheel speed w while
    the wheel slides (it rolls at w = u/r otherwise)."""

    def __init__(self, c, mu, p, m):
        self.C, self.mu, self.p = c, mu, p
        self.roll = m / (p['Iw'] + m)       # share of a torque that reaches the road while rolling
        self.y = 0.0
        self.w = None                        # None: rolling
        self.N = self.Fx = self.Fy = self.alpha = 0.0

    @property
    def sliding(self):
        return self.w is not None

    def force(self, dt, uw, vw, n, torque, n0):
        """Tire forces (Fx, Fy) in the wheel frame, for contact velocities uw, vw
        and a drive (+) or brake (-) torque on the wheel."""
        p = self.p
        self.N = n
        iw = p['Iw']
        if n <= 0:
            # airborne: the wheel spins freely, the tire carries nothing
            self.y = 0.0
            self.w = None
            self.Fx = self.Fy = 0.0
            return 0.0, 0.0
        mu_n = self.mu * n
        self.alpha = vw / abs(uw) if uw else vw     # $718990
        if self.w is not None:
            # sliding: the friction torque is the whole mu*N*r
            if self.w > uw:
                self.w = min(self.w + (torque - mu_n) / iw * dt, uw + SLIP_MAX)
                if self.w <= uw:
                    self.w = None
            else:
                self.w = max(self.w + (torque + mu_n) / iw * dt, uw - SLIP_MAX)
                if self.w >= uw:
                    self.w = None
            if self.w is not None:
                su = uw - self.w
                s = math.hypot(su, vw)
                if s:
                    self.Fx, self.Fy = -mu_n * su / s, -mu_n * vw / s
                else:
                    self.Fx, self.Fy = 0.0, 0.0
                return self.Fx, self.Fy
        t = torque * self.roll
        if abs(t) >= mu_n:
            # starts to slide: this step pushes mu*N along the wheel
            self.w = uw + clamp((torque - math.copysign(mu_n, t)) / iw * dt, SLIP_MAX)
            self.Fx, self.Fy = math.copysign(mu_n, t), 0.0
            return self.Fx, self.Fy
        fx = t
        mu1 = math.sqrt(max(self.mu ** 2 - (fx / n) ** 2, 0.0))   # friction circle
        c1 = self.C / n0
        k, c = p['k'], p['c']
        # z = |α| / α_sl with α_sl = 3μ'/C'; the arcade's α is v/|u|, and v at u = 0
        au = abs(uw) or 1.0
        z = abs(vw) * c1 / (3 * mu1 * au) if mu1 > 0 else 1.0
        if z >= 1:
            # past the curve's peak: the contact patch sticks, clamped at mu'N
            yd = -vw
            self.y = clamp(self.y + yd * dt, Y_MAX)
            fy = k * self.y + c * yd
            lim = mu1 * n
            if abs(fy) > lim:
                fy = math.copysign(lim, fy)
                self.y = fy / k
        else:
            secant = n * c1 * (1 - z + z * z / 3)     # Fiala force / |α|
            if abs(uw) * k * dt < 0.5 * secant:
                # relaxation: y' = -y |u| / σ - v, σ = secant / k
                yd = -self.y * abs(uw) * k / secant - vw
                self.y = clamp(self.y + yd * dt, Y_MAX)
                fy = k * self.y + c * yd
            else:
                fy = -math.copysign(mu1 * n * (1 - (1 - z) ** 3), vw)
                self.y = fy / k
        self.Fx, self.Fy = fx, fy
        return fx, fy


class Car:
    """State: lateral velocity v (ft/s), yaw rate r (rad/s), heading psi (rad,
    right positive) and position (x, z) in a world frame where heading 0 runs
    along +x and a right turn bends towards -z (hdstate.py's convention)."""

    def __init__(self, p=P, load='lag'):
        self.p, self.load = p, load
        self.m = p['W'] / G
        self.theta = self.q = 0.0             # pitch (nose down +) and its rate
        self.dn = 0.0                         # load moved to the rear, lb
        self.front = Axle(p['C'][0], p['mu'][0], p, self.m)
        self.rear = Axle(p['C'][1], p['mu'][1], p, self.m)
        self.v = self.r = self.psi = 0.0
        self.x = self.z = 0.0

    def set_pose(self, psi, x, z):
        self.psi, self.x, self.z = psi, x, z

    def loads(self, fx, dt):
        """Static and current axle loads; advances the pitch or lag state."""
        p = self.p
        a, b = p['a'], p['b']
        n0 = p['W'] * b / (a + b), p['W'] * a / (a + b)
        if self.load == 'pitch':
            (kf, kr), (cf, cr) = p['ks'], p['cs']
            th, q = self.theta, self.q
            nf = n0[0] + kf * a * th + cf * a * q
            nr = n0[1] - kr * b * th - cr * b * q
            # moment, nose down +: the tire forces act h below the CG
            mom = -fx * p['h'] - a * (nf - n0[0]) + b * (nr - n0[1])
            self.q += mom / p['Ip'] * dt
            self.theta += self.q * dt
            return n0, (nf, nr)
        dn = fx * p['h'] / (a + b)
        if self.load == 'lag':
            self.dn += (dn - self.dn) * min(dt / p['tau'], 1.0)
            dn = self.dn
        return n0, (n0[0] - dn, n0[1] + dn)

    def step(self, dt, u, delta, fx, brake):
        """Advance by dt. u: forward speed; delta: road wheel angle; fx: the
        tires' total longitudinal force (m·ax plus drag), which sets the load
        transfer; brake: the front brake torque at full effect (<= 0), faded
        by the front wheel's speed. The rear tire is asked for the rest of fx."""
        p, m = self.p, self.m
        fx = clamp(fx, FX_MAX)
        n0, (nf, nr) = self.loads(fx, dt)
        v, r = self.v, self.r
        cd, sd = math.cos(delta), math.sin(delta)
        vcf = v + p['a'] * r
        uwf, vwf = u * cd + vcf * sd, -u * sd + vcf * cd
        wf = self.front.w if self.front.w is not None else uwf
        fxf, fyf = self.front.force(dt, uwf, vwf, max(nf, 0.0), brake * brake_fade(wf), n0[0])
        fxbf = fxf * cd - fyf * sd                # front force in body axes
        fybf = fxf * sd + fyf * cd
        rear_t = clamp(fx - fxbf, FX_MAX) / self.rear.roll
        fxr, fyr = self.rear.force(dt, u, v - p['b'] * r, max(nr, 0.0), rear_t, n0[1])
        vdot = (fybf + fyr) / m - u * r
        rdot = (p['a'] * fybf - p['b'] * fyr) / p['I']
        # explicit Euler, as the arcade: pose from the old velocities
        c, s = math.cos(self.psi), math.sin(self.psi)
        self.x += (u * c - v * s) * dt
        self.z += (-u * s - v * c) * dt
        self.psi += r * dt
        self.v = clamp(self.v + vdot * dt, V_MAX)
        self.r = clamp(self.r + rdot * dt, R_MAX)
        return vdot + u * r                        # lateral acceleration


def understeer_speed(p=P):
    """Characteristic speed sqrt(L/K), K = (m/L)(b/Cf - a/Cr), in ft/s (model time)."""
    m, L = p['W'] / G, p['a'] + p['b']
    k = m / L * (p['b'] / p['C'][0] - p['a'] / p['C'][1])
    return math.sqrt(L / k)
