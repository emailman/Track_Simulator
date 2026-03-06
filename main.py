import math
import time
import tkinter as tk

from signals import Signal, LT_GREEN, LT_RED, LT_YELLOW
from track import Track
from train import Train

CANVAS_W = 800
CANVAS_H = 500
FPS = 60
FRAME_MS = 1000 // FPS

TRACK_COLOR = "#888888"
TRACK_WIDTH = 10
TRAIN_COLOR  = "#4488FF"
TRAIN2_COLOR = "#FF8C00"
BG_COLOR = "#2d5a27"
PANEL_COLOR = "#1a3a16"

BLOCK_SPEEDS = {"BL1": 150, "BL2": 75, "BL3": 75, "BL4": 150, "BL5": 300}


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
        _bl4_seg, _bl4_t0, _bl4_t1 = self.track.block_ranges["BL4"]
        self.train = Train(segment=_bl4_seg, speed=BLOCK_SPEEDS["BL4"], route="main")
        self.train.t = (_bl4_t0 + _bl4_t1) / 2

        _bl1_seg, _bl1_t0, _bl1_t1 = self.track.block_ranges["BL1"]
        self.train2 = Train(segment=_bl1_seg, speed=BLOCK_SPEEDS["BL1"], route="main")
        self.train2.t = (_bl1_t0 + _bl1_t1) / 2

        self._switch_transition_end: float = 0.0
        self._sw2_state: str = "main"
        self._sw2_transition_end: float = 0.0
        self._train_last_block: str = ""
        self._train2_last_block: str = ""
        _bl1_seg, _bl1_t0, _bl1_t1 = self.track.block_ranges["BL1"]
        self._bl1_seg = _bl1_seg
        self._bl1_t0: float = _bl1_t0
        self._train_held_bl1: bool = False
        self._train2_held_bl1: bool = False
        _bl4_seg, _bl4_t0, _bl4_t1 = self.track.block_ranges["BL4"]
        self._bl4_seg = _bl4_seg
        self._bl4_t0: float = _bl4_t0
        self._train_held_bl4: bool = False
        self._train2_held_bl4: bool = False
        _bl2_seg, _bl2_t0, _bl2_t1 = self.track.block_ranges["BL2"]
        self._bl2_center_seg = _bl2_seg
        self._bl2_center_t: float = (_bl2_t0 + _bl2_t1) / 2
        self._train2_stop_until: float = 0.0
        self._train2_bl2_stopped: bool = False
        _bl3_seg, _bl3_t0, _bl3_t1 = self.track.block_ranges["BL3"]
        self._bl3_center_seg = _bl3_seg
        self._bl3_center_t: float = (_bl3_t0 + _bl3_t1) / 2
        self._train_stop_until: float = 0.0
        self._train_bl3_stopped: bool = False
        self._draw_track()
        self._draw_block_sections()
        self._draw_signals()
        self._train_sprite  = self._create_train_sprite(self.train,  TRAIN_COLOR)
        self._train2_sprite = self._create_train_sprite(self.train2, TRAIN2_COLOR)
        self._route_label = self.canvas.create_text(
            10, 10, anchor="nw", fill="white",
            font=("Courier", 12), text=self._route_text()
        )
        self._block_label = self.canvas.create_text(
            10, 30, anchor="nw", fill=TRAIN_COLOR,
            font=("Courier", 12), text="T1 Block: ?  Speed: ?"
        )

        self._block2_label = self.canvas.create_text(
            10, 50, anchor="nw", fill=TRAIN2_COLOR,
            font=("Courier", 12), text="T2 Block: ?  Speed: ?"
        )

        self._last_time = time.perf_counter()
        self._loop()

    def _set_sw1(self, route: str) -> None:
        """Set SW1 (diverging junction): controls which path trains take from seg0."""
        if route == self.train.route and not self._switch_transition_end:
            return
        self.train.route = route
        self.train2.route = route
        self._switch_transition_end = time.perf_counter() + 1.0
        self.canvas.itemconfig(self._switch_markers[0], fill="#FF0000")
        self._update_signal_switch_indicators()
        self.canvas.itemconfig(self._route_label, text=self._route_text())

    def _set_sw2(self, route: str) -> None:
        """Set SW2 (converging junction): visual/signal state only."""
        if route == self._sw2_state and not self._sw2_transition_end:
            return
        self._sw2_state = route
        self._sw2_transition_end = time.perf_counter() + 1.0
        self.canvas.itemconfig(self._switch_markers[1], fill="#FF0000")
        self._update_signal_switch_indicators()

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

        # Block labels — placed near the center of each section
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
        self._update_signal_switch_indicators()

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
                fill="#00CC00", outline="#333333", width=2
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

    def _update_signal_switch_indicators(self) -> None:
        """Set frame 0 (top) and frame 1 (bottom) of every signal to reflect switch state."""
        # SG1 reflects SW1; SG2 and SG3 reflect SW2
        if self._switch_transition_end:
            sw1_bottom = LT_RED
        elif self.train.route == "main":
            sw1_bottom = LT_GREEN
        else:
            sw1_bottom = LT_YELLOW

        if self._sw2_transition_end:
            sw2_bottom = LT_RED
        elif self._sw2_state == "main":
            sw2_bottom = LT_GREEN
        else:
            sw2_bottom = LT_YELLOW

        # Per-signal top-head mapping (bottom → top):
        # SG1: mirrors bottom exactly
        # SG2: green→green, red→red, yellow→red  (never yellow)
        # SG3: green→red,   red→red, yellow→yellow  (never green)
        top_maps = [
            {LT_GREEN: LT_GREEN, LT_RED: LT_RED,   LT_YELLOW: LT_YELLOW},  # SG1
            {LT_GREEN: LT_GREEN, LT_RED: LT_RED,   LT_YELLOW: LT_RED},     # SG2
            {LT_GREEN: LT_RED,   LT_RED: LT_RED,   LT_YELLOW: LT_YELLOW},  # SG3
        ]
        bottoms = [sw1_bottom, sw2_bottom, sw2_bottom]

        for sig, bottom, top_map in zip(self.signals, bottoms, top_maps):
            sig.set_frame(1, bottom)
            sig.set_frame(0, top_map[bottom])

    def _update_switch_markers(self) -> None:
        sw1_color = "#00CC00" if self.train.route == "main" else "#FFFF00"
        sw2_color = "#00CC00" if self._sw2_state == "main" else "#FFFF00"
        self.canvas.itemconfig(self._switch_markers[0], fill=sw1_color)
        self.canvas.itemconfig(self._switch_markers[1], fill=sw2_color)

    # ------------------------------------------------------------------
    # Train sprite
    # ------------------------------------------------------------------

    def _create_train_sprite(self, train: Train, color: str) -> int:
        x, y = train.xy
        return self.canvas.create_rectangle(
            x - 12, y - 6, x + 12, y + 6,
            fill=color, outline="#AAAAAA", width=1
        )

    def _update_sprite(self, sprite_id: int, train: Train, color: str) -> int:
        x, y = train.xy
        angle = train.angle
        hw, hh = 12, 5
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        rotated = []
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        for dx, dy in corners:
            rx = dx * cos_a - dy * sin_a + x
            ry = dx * sin_a + dy * cos_a + y
            rotated.extend([rx, ry])
        self.canvas.delete(sprite_id)
        return self.canvas.create_polygon(
            *rotated, fill=color, outline="#AAAAAA", width=1
        )

    # ------------------------------------------------------------------
    # Animation loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_time
        self._last_time = now

        self.train.update(dt)
        self.train2.update(dt)
        self._train_sprite  = self._update_sprite(self._train_sprite,  self.train,  TRAIN_COLOR)
        self._train2_sprite = self._update_sprite(self._train2_sprite, self.train2, TRAIN2_COLOR)

        if self._switch_transition_end and now >= self._switch_transition_end:
            self._switch_transition_end = 0.0
            self._update_switch_markers()
            self._update_signal_switch_indicators()
        if self._sw2_transition_end and now >= self._sw2_transition_end:
            self._sw2_transition_end = 0.0
            self._update_switch_markers()
            self._update_signal_switch_indicators()

        block  = self.train.current_block(self.track.block_ranges)
        block2 = self.train2.current_block(self.track.block_ranges)
        if block  in BLOCK_SPEEDS: self.train.speed  = BLOCK_SPEEDS[block]
        if block2 in BLOCK_SPEEDS: self.train2.speed = BLOCK_SPEEDS[block2]

        train_in_bl1  = block  == "BL1"
        train2_in_bl1 = block2 == "BL1"
        train_in_bl4  = block  == "BL4"
        train2_in_bl4 = block2 == "BL4"

        # Block-entry triggers: SW1 control, BL1 and BL4 mutual exclusion
        if block != self._train_last_block:
            if block == "BL1":
                self._set_sw1("siding")
                if train2_in_bl1:
                    self._train_held_bl1 = True
            if block == "BL4" and train2_in_bl4:
                self._train_held_bl4 = True
            self._train_last_block = block
        if block2 != self._train2_last_block:
            if block2 == "BL1":
                self._set_sw1("main")
                if train_in_bl1:
                    self._train2_held_bl1 = True
            if block2 == "BL4" and train_in_bl4:
                self._train2_held_bl4 = True
            self._train2_last_block = block2

        # Release BL1 hold when the occupying train clears the section
        if self._train_held_bl1 and not train2_in_bl1:
            self._train_held_bl1 = False
        if self._train2_held_bl1 and not train_in_bl1:
            self._train2_held_bl1 = False

        # Apply BL1 hold: clamp position at section entry and stop
        if self._train_held_bl1:
            if self.train.segment is self._bl1_seg:
                self.train.t = min(self.train.t, self._bl1_t0)
            self.train.speed = 0
        if self._train2_held_bl1:
            if self.train2.segment is self._bl1_seg:
                self.train2.t = min(self.train2.t, self._bl1_t0)
            self.train2.speed = 0

        # Release BL4 hold when the occupying train clears the section
        if self._train_held_bl4 and not train2_in_bl4:
            self._train_held_bl4 = False
        if self._train2_held_bl4 and not train_in_bl4:
            self._train2_held_bl4 = False

        # Apply BL4 hold: clamp position at section entry and stop
        if self._train_held_bl4:
            if self.train.segment is self._bl4_seg:
                self.train.t = min(self.train.t, self._bl4_t0)
            self.train.speed = 0
        if self._train2_held_bl4:
            if self.train2.segment is self._bl4_seg:
                self.train2.t = min(self.train2.t, self._bl4_t0)
            self.train2.speed = 0

        # Orange train: stop 3 s at center of BL2, then set SW2 straight
        if block2 != "BL2":
            self._train2_bl2_stopped = False
        elif (not self._train2_bl2_stopped
              and self.train2.segment is self._bl2_center_seg
              and self.train2.t >= self._bl2_center_t):
            self._train2_bl2_stopped = True
            self._train2_stop_until = now + 3.0
        if self._train2_stop_until:
            if now < self._train2_stop_until or train_in_bl4:
                self.train2.speed = 0
            else:
                self._train2_stop_until = 0.0
                self._set_sw2("main")

        # Blue train: stop 3 s at center of BL3, then set SW2 diverge
        if block != "BL3":
            self._train_bl3_stopped = False
        elif (not self._train_bl3_stopped
              and self.train.segment is self._bl3_center_seg
              and self.train.t >= self._bl3_center_t):
            self._train_bl3_stopped = True
            self._train_stop_until = now + 3.0
        if self._train_stop_until:
            if now < self._train_stop_until or train2_in_bl4:
                self.train.speed = 0
            else:
                self._train_stop_until = 0.0
                self._set_sw2("siding")
        self.canvas.itemconfig(self._block_label,  text=f"T1 Block: {block}  Speed: {int(self.train.speed)}")
        self.canvas.itemconfig(self._block2_label, text=f"T2 Block: {block2}  Speed: {int(self.train2.speed)}")

        # noinspection PyTypeChecker
        self.root.after(FRAME_MS, self._loop)

    # ------------------------------------------------------------------
    # Route display
    # ------------------------------------------------------------------

    def _route_text(self) -> str:
        return "Route: BL2" if self.train.route == "main" else "Route: BL3"


if __name__ == "__main__":
    app = App()
    app.root.mainloop()
