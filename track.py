import math


class Segment:
    """A track segment represented as a dense polyline of (x, y) waypoints."""

    def __init__(self, points: list[tuple[float, float]]):
        self.points = points
        self.next: list["Segment"] = []
        # Pre-compute cumulative arc lengths for accurate parametric lookup
        self._cum_lengths: list[float] = [0.0]
        for i in range(1, len(points)):
            dx = points[i][0] - points[i - 1][0]
            dy = points[i][1] - points[i - 1][1]
            self._cum_lengths.append(self._cum_lengths[-1] + math.hypot(dx, dy))
        self.length: float = self._cum_lengths[-1]

    def position_at(self, t: float) -> tuple[float, float]:
        """Return (x, y) interpolated at parameter t ∈ [0, 1]."""
        t = max(0.0, min(1.0, t))
        target = t * self.length
        lo, hi = 0, len(self._cum_lengths) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if self._cum_lengths[mid] <= target:
                lo = mid
            else:
                hi = mid
        seg_len = self._cum_lengths[hi] - self._cum_lengths[lo]
        if seg_len == 0:
            return self.points[lo]
        frac = (target - self._cum_lengths[lo]) / seg_len
        x = self.points[lo][0] + frac * (self.points[hi][0] - self.points[lo][0])
        y = self.points[lo][1] + frac * (self.points[hi][1] - self.points[lo][1])
        return x, y

    def angle_at(self, t: float) -> float:
        """Return heading in radians at parameter t."""
        eps = 0.005
        x1, y1 = self.position_at(max(0.0, t - eps))
        x2, y2 = self.position_at(min(1.0, t + eps))
        return math.atan2(y2 - y1, x2 - x1)


def _arc_points(cx: float, cy: float, rx: float, ry: float,
                start_deg: float, end_deg: float, steps: int = 60) -> list[tuple[float, float]]:
    """Dense polyline approximating an elliptical arc from start_deg to end_deg."""
    pts = []
    for i in range(steps + 1):
        angle = math.radians(start_deg + (end_deg - start_deg) * i / steps)
        pts.append((cx + rx * math.cos(angle), cy + ry * math.sin(angle)))
    return pts


def _line_points(x0: float, y0: float, x1: float, y1: float,
                 steps: int = 10) -> list[tuple[float, float]]:
    """Dense polyline for a straight segment."""
    return [(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
            for i in range(steps + 1)]


class Track:
    """Collection of connected Segments forming the track graph."""

    def __init__(self, segments: list[Segment]):
        self.segments = segments

    @classmethod
    def build_oval_with_siding(cls) -> "Track":
        """
        Build a main oval loop with one passing siding below it.

        Layout (counterclockwise, canvas 800x500):
          Main oval: centre (400, 220), rx=280, ry=150
          Switch 1 (sw1): bottom-right of oval, angle 65°
          Switch 2 (sw2): bottom-left  of oval, angle 115°

          seg0 – main arc from sw2 (115°) counterclockwise around the
                  top and back to sw1 (65°+360°).  Ends at sw1.
                  next = [seg1 (bypass), seg2 (siding)]

          seg1 – bypass arc from sw1 (65°) to sw2 (115°) along the
                  bottom of the oval.  next = [seg0]

          seg2 – siding: sw1 → straight down → bottom corners →
                  straight across → sw2.  next = [seg0]
        """
        cx, cy = 400, 220
        rx, ry = 280, 150

        sw1_deg = 65.0
        sw2_deg = 115.0

        sw1 = (cx + rx * math.cos(math.radians(sw1_deg)),
               cy + ry * math.sin(math.radians(sw1_deg)))
        sw2 = (cx + rx * math.cos(math.radians(sw2_deg)),
               cy + ry * math.sin(math.radians(sw2_deg)))

        # seg0: main arc (counterclockwise around the top)
        seg0_pts = _arc_points(cx, cy, rx, ry, sw2_deg, sw1_deg + 360, steps=120)
        seg0 = Segment(seg0_pts)

        # seg1: bypass arc along the bottom of the oval
        seg1_pts = _arc_points(cx, cy, rx, ry, sw1_deg, sw2_deg, steps=30)
        seg1 = Segment(seg1_pts)

        # seg2: siding — a U-shape below the oval with rounded corners
        siding_depth = 65   # pixels below sw1/sw2
        corner_r = 18        # corner radius

        # sw1 and sw2 have approximately the same y since they're symmetric
        siding_y = max(sw1[1], sw2[1]) + siding_depth

        seg2_pts = (
            [sw1]
            # drop straight down from sw1 to the top of the bottom-right corner
            + _line_points(sw1[0], sw1[1], sw1[0], siding_y - corner_r, steps=8)[1:]
            # bottom-right corner: arc 0° → 90° (right side to bottom of circle)
            #   circle centre = (sw1[0] - corner_r, siding_y - corner_r)
            + _arc_points(sw1[0] - corner_r, siding_y - corner_r,
                          corner_r, corner_r, 0, 90, steps=8)[1:]
            # straight across the bottom
            + _line_points(sw1[0] - corner_r, siding_y,
                           sw2[0] + corner_r, siding_y, steps=20)[1:]
            # bottom-left corner: arc 90° → 180° (bottom to left side of circle)
            #   circle centre = (sw2[0] + corner_r, siding_y - corner_r)
            + _arc_points(sw2[0] + corner_r, siding_y - corner_r,
                          corner_r, corner_r, 90, 180, steps=8)[1:]
            # rise straight up to sw2
            + _line_points(sw2[0], siding_y - corner_r, sw2[0], sw2[1], steps=8)[1:]
        )
        seg2 = Segment(seg2_pts)

        # Wire the segment graph
        seg0.next = [seg1, seg2]   # [0] = bypass (main), [1] = siding
        seg1.next = [seg0]
        seg2.next = [seg0]

        return cls([seg0, seg1, seg2])
