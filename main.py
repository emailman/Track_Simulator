import math
import time
import tkinter as tk

from signals import Signal
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
PANEL_COLOR = "#1a3a16"


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Track Simulator")
        self.root.resizable(False, False)

        main_frame = tk.Frame(self.root, bg=PANEL_COLOR)
        main_frame.pack()

        self.canvas = tk.Canvas(
            main_frame, width=CANVAS_W, height=CANVAS_H,
            bg=BG_COLOR, highlightthickness=0
        )
        self.canvas.pack(side=tk.LEFT)

        self._sw1_var = tk.IntVar(value=0)
        self._create_switch_panel(main_frame)

        self.track = Track.build_rounded_rect_with_siding()
        self.train = Train(segment=self.track.segments[0], speed=150.0, route="main")

        self._draw_track()
        self._draw_block_sections()
        self._draw_signals()
        self._train_sprite = self._create_train_sprite()
        self._route_label = self.canvas.create_text(
            10, 10, anchor="nw", fill="white",
            font=("Courier", 12), text=self._route_text()
        )
        self._block_label = self.canvas.create_text(
            10, 30, anchor="nw", fill="yellow",
            font=("Courier", 12), text="Block: ?"
        )

        self._last_time = time.perf_counter()
        self._loop()

    # ------------------------------------------------------------------
    # Switch panel
    # ------------------------------------------------------------------

    def _create_switch_panel(self, parent: tk.Frame) -> None:
        panel = tk.Frame(parent, bg=PANEL_COLOR, width=120, height=CANVAS_H)
        panel.pack(side=tk.LEFT, fill=tk.Y)
        panel.pack_propagate(False)

        inner = tk.Frame(panel, bg=PANEL_COLOR)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(inner, text="SW1/SW2", bg=PANEL_COLOR, fg="white",
                 font=("Helvetica", 9, "bold")).pack(pady=(0, 4))
        tk.Label(inner, text="MAIN", bg=PANEL_COLOR, fg="#aaaaaa",
                 font=("Helvetica", 7)).pack()

        tk.Scale(
            inner, variable=self._sw1_var, from_=0, to=1,
            orient=tk.VERTICAL, showvalue=False,
            bg=PANEL_COLOR, fg="white", troughcolor="#333333",
            activebackground="#FFA500", highlightthickness=0,
            resolution=1, length=100,
            command=lambda _v: self._on_switch(),
        ).pack()

        tk.Label(inner, text="SIDING", bg=PANEL_COLOR, fg="#aaaaaa",
                 font=("Helvetica", 7)).pack()

    def _on_switch(self) -> None:
        """Called when the SW1 slider moves."""
        self.train.route = "siding" if self._sw1_var.get() == 1 else "main"
        self._update_switch_markers()
        self.canvas.itemconfig(self._route_label, text=self._route_text())

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

    def _draw_block_sections(self) -> None:
        """Draw block boundary dots and BL1–BL5 labels."""
        # Block boundaries: 4 insulated-joint positions on the main loop
        # matching x-positions of SW1/SW2 on both top and bottom straights.
        sw1_x, sw2_x = 220, 580
        top_y, bottom_y = 120, 280
        siding_y = 360

        boundary_pts = [
            (sw1_x, top_y),
            (sw2_x, top_y),
            (sw1_x, bottom_y),
            (sw2_x, bottom_y),
        ]
        r = 4
        for bx, by in boundary_pts:
            self.canvas.create_oval(
                bx - r, by - r, bx + r, by + r,
                fill="black", outline="black"
            )

        # Block labels — placed near the centre of each section
        block_labels = [
            ("BL1",  90, 200),                          # left semicircle
            ("BL2", (sw1_x + sw2_x) // 2, bottom_y - 14),  # bottom main straight
            ("BL3", (sw1_x + sw2_x) // 2, siding_y - 14),   # siding
            ("BL4", 713, 200),                          # right semicircle
            ("BL5", (sw1_x + sw2_x) // 2, top_y - 14), # top straight
        ]
        for name, lx, ly in block_labels:
            self.canvas.create_text(
                lx, ly, text=name, fill="white",
                font=("Helvetica", 9, "bold")
            )

    def _draw_signals(self) -> None:
        """Draw the three static signals on the canvas."""
        #  SG1 — left switch area (between left semicircle and sw1=(220,280))
        #  SG2 — right switch area (just right of sw2=(580,280))
        #  SG3 — right end of the horizontal siding (siding_y=360)
        self.signals = [
            Signal(self.canvas, 190,  280, "SG1"),
            Signal(self.canvas, 550,  280, "SG2"),
            Signal(self.canvas, 505,  363, "SG3", flip=True),
        ]

    def _draw_switch_markers(self) -> None:
        r = 6
        self._switch_markers = []
        self._switch_labels = []
        marked: set[tuple[int, int]] = set()
        sw_names = iter(["SW1", "SW2"])

        def _add_marker(x: float, y: float) -> None:
            pnt = (round(x), round(y))
            if pnt in marked:
                return
            marked.add(pnt)
            oid = self.canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill="#00BB00", outline="#FFA500", width=2
            )
            self._switch_markers.append(oid)
            lid = self.canvas.create_text(
                x, y - r - 6, text=next(sw_names, ""),
                fill="white", font=("Helvetica", 8, "bold")
            )
            self._switch_labels.append(lid)

        # Diverging switches: segment ends where multiple next-segments branch
        for seg in self.track.segments:
            if len(seg.next) > 1:
                _add_marker(*seg.points[-1])

        # Converging switches: multiple segments share the same endpoint
        from collections import defaultdict
        end_counts: dict[tuple[int, int], list] = defaultdict(list)
        for seg in self.track.segments:
            pt = (round(seg.points[-1][0]), round(seg.points[-1][1]))
            end_counts[pt].append(seg)
        for pt, segments in end_counts.items():
            if len(segments) > 1:
                _add_marker(*pt)

    def _update_switch_markers(self) -> None:
        color = "#00BB00" if self.train.route == "main" else "#FFD700"
        for oid in self._switch_markers:
            self.canvas.itemconfig(oid, fill=color)

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

        block = self.train.current_block(self.track.block_ranges)
        self.canvas.itemconfig(self._block_label, text=f"Block: {block}")

        # noinspection PyTypeChecker
        self.root.after(FRAME_MS, self._loop)

    # ------------------------------------------------------------------
    # Route display
    # ------------------------------------------------------------------

    def _route_text(self) -> str:
        return f"Route: {self.train.route.upper()}"


if __name__ == "__main__":
    app = App()
    app.root.mainloop()
