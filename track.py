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

    def t_near(self, x: float, y: float) -> float:
        """Return the t value of the polyline waypoint closest to (x, y)."""
        best_i, best_d = 0, float("inf")
        for i, (px, py) in enumerate(self.points):
            d = (px - x) ** 2 + (py - y) ** 2
            if d < best_d:
                best_d, best_i = d, i
        return self._cum_lengths[best_i] / self.length


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
    def build_rounded_rect_with_siding(cls) -> "Track":
        """
        Build a main rounded-rectangle loop with one passing siding below it.

        Layout (clockwise on screen, canvas 800×500):
          Main loop: left-end center (140, 200), right-end center (660, 200),
                     end-radius = 80.
          B5  – top straight:    y=120, x ∈ [140, 660]
          B2  – bottom straight: y=280, x ∈ [140, 660]
          S1 / sw1 = (220, 280)  near left end  – train diverges to siding here
          S2 / sw2 = (580, 280)  near right end – siding rejoins here
          B3  – siding U-shape below the bottom straight

          seg0 – long way round: sw2 → right semicircle (B4) → top (B5) →
                  left semicircle (B1) → sw1.
                  next = [seg1 (main bottom), seg2 (siding)]
          seg1 – bottom straight B2: sw1 → sw2.  next = [seg0]
          seg2 – siding B3: sw1 → down → across → up → sw2.  next = [seg0]
        """
        left_cx, right_cx, mid_y = 140, 660, 200
        r_end = 80
        top_y    = mid_y - r_end   # 120
        bottom_y = mid_y + r_end   # 280

        sw1 = (220, bottom_y)   # switch near left end
        sw2 = (580, bottom_y)   # switch near right end

        # seg0: clockwise on screen from sw2 → right semicircle → top → left semicircle → sw1
        seg0_pts = (
            _line_points(sw2[0], sw2[1], right_cx, bottom_y, steps=5)
            # right semicircle: bottom (90°) → top (−90°) via right side
            + _arc_points(right_cx, mid_y, r_end, r_end, 90, -90, steps=40)[1:]
            # top straight: right → left
            + _line_points(right_cx, top_y, left_cx, top_y, steps=30)[1:]
            # left semicircle: top (270°) → bottom (90°) via left side
            + _arc_points(left_cx, mid_y, r_end, r_end, 270, 90, steps=40)[1:]
            # short bottom-left straight to sw1
            + _line_points(left_cx, bottom_y, sw1[0], sw1[1], steps=5)[1:]
        )
        seg0 = Segment(seg0_pts)

        # seg1: bottom straight, sw1 → sw2
        seg1_pts = _line_points(sw1[0], sw1[1], sw2[0], sw2[1], steps=20)
        seg1 = Segment(seg1_pts)

        # seg2: siding B3 – 45° switch entries, horizontal lower straight
        siding_depth = 80   # pixels below bottom straight
        corner_r = 25
        sq2 = math.sqrt(2)

        siding_y = bottom_y + siding_depth   # 360

        # Arc centres: chosen so each arc is simultaneously tangent to the 45°
        # diagonal from the switch and to the horizontal siding track.
        #   O.y = siding_y − corner_r  (tangent to horizontal from above)
        #   O.x = sw_x ± (depth + corner_r*(√2−1))  (tangent to 45° line)
        lc_x = sw1[0] + siding_depth + corner_r * (sq2 - 1)  # left  corner center x
        lc_y = siding_y - corner_r                            # left  corner center y
        rc_x = sw2[0] - siding_depth - corner_r * (sq2 - 1)  # right corner center x
        rc_y = siding_y - corner_r                            # right corner center y

        seg2_pts = (
            [sw1]
            # 45° diagonal: sw1 down-right to the left-corner tangent point
            + _line_points(sw1[0], sw1[1],
                           lc_x - corner_r / sq2, lc_y + corner_r / sq2, steps=8)[1:]
            # left corner arc: 135° → 90°  (45° line → horizontal)
            + _arc_points(lc_x, lc_y, corner_r, corner_r, 135, 90, steps=8)[1:]
            # straight across the bottom
            + _line_points(lc_x, siding_y, rc_x, siding_y, steps=20)[1:]
            # right corner arc: 90° → 45°  (horizontal → 45° line)
            + _arc_points(rc_x, rc_y, corner_r, corner_r, 90, 45, steps=8)[1:]
            # 45° diagonal: right-corner tangent point up-right to sw2
            + _line_points(rc_x + corner_r / sq2, rc_y + corner_r / sq2,
                           sw2[0], sw2[1], steps=8)[1:]
        )
        seg2 = Segment(seg2_pts)

        # Wire the segment graph
        seg0.next = [seg1, seg2]   # [0] = main bottom, [1] = siding
        seg1.next = [seg0]
        seg2.next = [seg0]

        t_bl4_bl5 = seg0.t_near(580, 120)   # boundary between BL4 and BL5
        t_bl5_bl1 = seg0.t_near(220, 120)   # boundary between BL5 and BL1

        track = cls([seg0, seg1, seg2])
        track.block_ranges = {
            "BL1": (seg0, t_bl5_bl1, 1.0),
            "BL2": (seg1, 0.0,       1.0),
            "BL3": (seg2, 0.0,       1.0),
            "BL4": (seg0, 0.0,       t_bl4_bl5),
            "BL5": (seg0, t_bl4_bl5, t_bl5_bl1),
        }
        return track
