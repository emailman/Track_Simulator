import math
import time
import tkinter as tk

from track import Track
from train import Train

CANVAS_W = 800
CANVAS_H = 500
FPS = 60
FRAME_MS = 1000 // FPS

TRACK_COLOR = "#888888"
TRACK_WIDTH = 10
TRAIN_COLOR = "#FFFFFF"
BG_COLOR = "#2d5a27"


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Track Simulator")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(
            self.root, width=CANVAS_W, height=CANVAS_H,
            bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack()

        self.track = Track.build_rounded_rect_with_siding()
        self.train = Train(segment=self.track.segments[0], speed=150.0, route="main")

        self._draw_track()
        self._train_sprite = self._create_train_sprite()
        self._route_label = self.canvas.create_text(
            10, 10, anchor="nw", fill="white",
            font=("Courier", 12), text=self._route_text()
        )

        # Key binding: 's' toggles the siding route
        self.root.bind("<s>", lambda _e: self._toggle_route())
        self.root.bind("<S>", lambda _e: self._toggle_route())

        self._last_time = time.perf_counter()
        self._loop()

    # ------------------------------------------------------------------
    # Track drawing
    # ------------------------------------------------------------------

    def _draw_track(self) -> None:
        """Draw all segments as thick polylines on the canvas."""
        for seg in self.track.segments:
            flat = [coord for pt in seg.points for coord in pt]
            if len(flat) >= 4:
                self.canvas.create_line(
                    *flat,
                    fill=TRACK_COLOR, width=TRACK_WIDTH,
                    capstyle="round", joinstyle="round"
                )
        # Draw switch markers at junction points
        self._draw_switch_markers()

    def _draw_switch_markers(self) -> None:
        r = 6
        for seg in self.track.segments:
            if len(seg.next) > 1:
                # This segment leads to a switch — mark the end point
                x, y = seg.points[-1]
                self.canvas.create_oval(
                    x - r, y - r, x + r, y + r,
                    fill="#FFD700", outline="#FFA500", width=2
                )

    # ------------------------------------------------------------------
    # Train sprite
    # ------------------------------------------------------------------

    def _create_train_sprite(self) -> int:
        x, y = self.train.xy
        return self.canvas.create_rectangle(
            x - 12, y - 6, x + 12, y + 6,
            fill=TRAIN_COLOR, outline="#AAAAAA", width=1
        )

    def _update_train_sprite(self) -> None:
        x, y = self.train.xy
        angle = self.train.angle
        # Rotate the four corners of the train rectangle
        hw, hh = 12, 5
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        rotated = []
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        for dx, dy in corners:
            rx = dx * cos_a - dy * sin_a + x
            ry = dx * sin_a + dy * cos_a + y
            rotated.extend([rx, ry])
        # Recreate as polygon for rotation support
        self.canvas.delete(self._train_sprite)
        self._train_sprite = self.canvas.create_polygon(
            *rotated, fill=TRAIN_COLOR, outline="#AAAAAA", width=1
        )

    # ------------------------------------------------------------------
    # Animation loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_time
        self._last_time = now

        self.train.update(dt)
        self._update_train_sprite()

        # noinspection PyTypeChecker
        self.root.after(FRAME_MS, self._loop)

    # ------------------------------------------------------------------
    # Route toggle
    # ------------------------------------------------------------------

    def _toggle_route(self) -> None:
        self.train.toggle_route()
        self.canvas.itemconfig(self._route_label, text=self._route_text())

    def _route_text(self) -> str:
        route = self.train.route.upper()
        return f"Route: {route}  (press S to toggle)"


if __name__ == "__main__":
    app = App()
    app.root.mainloop()
