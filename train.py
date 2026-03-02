from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from track import Segment


class Train:
    """A train that moves along a segment graph at a fixed speed."""

    def __init__(self, segment: "Segment", speed: float = 80.0, route: str = "main"):
        """
        Args:
            segment: The starting Segment.
            speed:   Travel speed in canvas-pixels per second.
            route:   "main" to take the bypass at each switch,
                     "siding" to take the siding branch.
        """
        self.segment = segment
        self.t = 0.0          # position along current segment [0, 1]
        self.speed = speed    # pixels / second
        self.route = route    # "main" or "siding"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def xy(self) -> tuple[float, float]:
        return self.segment.position_at(self.t)

    @property
    def angle(self) -> float:
        return self.segment.angle_at(self.t)

    def update(self, dt: float) -> None:
        """Advance the train by dt seconds."""
        if self.segment.length == 0:
            return
        advance = self.speed * dt / self.segment.length  # fraction of segment
        self.t += advance
        while self.t >= 1.0:
            self.t -= 1.0
            self._cross_to_next_segment()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _cross_to_next_segment(self) -> None:
        """Move to the next segment according to the current route."""
        nexts = self.segment.next
        if not nexts:
            self.t = 0.0
            return
        if len(nexts) == 1:
            self.segment = nexts[0]
        else:
            # nexts[0] = main bypass, nexts[1] = siding
            self.segment = nexts[1] if self.route == "siding" else nexts[0]

    def toggle_route(self) -> None:
        """Switch between 'main' and 'siding' route at the next junction."""
        self.route = "siding" if self.route == "main" else "main"
