"""
Signal display for Track Simulator.

Each signal has two stacked frames, each containing three lights:
  Frame 0 (top)    – movement aspect:  G=Proceed, R=Stop,              Y=Proceed Slowly
  Frame 1 (bottom) – route aspect:     G=Straight, R=Transition/Blocked, Y=Diverge

Canvas items are stored in light_ids[frame][light] so individual lights can
be toggled later via canvas.itemconfig(..., fill=...).
"""

import tkinter as tk

# ── Geometry ───────────────────────────────────────────────────────────────
LIGHT_R   = 5     # light circle radius (px)
PAD       = 3     # padding inside each frame (px)
FRAME_W   = LIGHT_R * 2 + PAD * 2          # 16 px
FRAME_H   = (LIGHT_R * 2) * 3 + PAD * 4   # 42 px  (3 lights + 4 gaps)
FRAME_GAP = 3     # vertical gap between the two frames
HEAD_H    = FRAME_H * 2 + FRAME_GAP        # 87 px  total head height
MAST_H    = 8     # mast stub below head (px)

# ── Colours ────────────────────────────────────────────────────────────────
_ON  = ["#00DD00", "#DD0000", "#DDDD00"]   # green / red / yellow (lit)
_OFF = ["#004400", "#440000", "#444400"]   # dim versions (unlit)

# Light indices
LT_GREEN  = 0
LT_RED    = 1
LT_YELLOW = 2


class Signal:
    """A two-frame, three-light railway signal drawn on a tk.Canvas."""

    def __init__(self, canvas: tk.Canvas, bx: float, by: float, label: str,
                 flip: bool = False):
        """
        Parameters
        ----------
        canvas : tk.Canvas  – target canvas
        bx, by : float      – mast base coordinates (at track level)
        label  : str        – text label (e.g. "S1")
        flip   : bool       – if True, label is above and head hangs below
        """
        self.canvas = canvas
        self.bx = bx
        self.by = by
        self.label = label
        self.flip = flip

        # light_ids[frame_index][light_index] → canvas oval item ID
        self.light_ids: list[list[int]] = [[], []]

        self._draw()

    # ──────────────────────────────────────────────────────────────────────
    # Drawing
    # ──────────────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        bx, by = self.bx, self.by
        lr  = LIGHT_R
        fw  = FRAME_W
        fh  = FRAME_H
        pad = PAD
        gap = FRAME_GAP
        hx  = bx - fw // 2   # left edge of both frames

        if self.flip:
            # Label sits above the mast base; head hangs below
            label_y  = by - 10
            mast_end = by + MAST_H
            head_top = mast_end
        else:
            # Head rises above mast base; label sits above the head
            mast_end  = by - MAST_H
            head_top  = mast_end - HEAD_H
            label_y   = head_top - 10

        # Mast stub
        self.canvas.create_line(
            bx, by, bx, mast_end,
            fill="#888888", width=2
        )

        # Two frames
        for fi in range(2):
            fy = head_top + fi * (fh + gap)

            # Frame housing
            self.canvas.create_rectangle(
                hx, fy, hx + fw, fy + fh,
                fill="#1a1a1a", outline="#666666", width=1
            )

            self.light_ids[fi] = []
            for li in range(3):
                lx = bx
                ly = fy + pad + lr + li * (lr * 2 + pad)
                cid = self.canvas.create_oval(
                    lx - lr, ly - lr, lx + lr, ly + lr,
                    fill=_ON[li], outline=""
                )
                self.light_ids[fi].append(cid)

        # Label
        self.canvas.create_text(
            bx, label_y,
            text=self.label, fill="white",
            font=("Courier", 9, "bold")
        )

    # ──────────────────────────────────────────────────────────────────────
    # Public helpers (for future simulation logic)
    # ──────────────────────────────────────────────────────────────────────

    def set_light(self, frame: int, light: int, on: bool) -> None:
        """Turn a single light on (bright) or off (dim)."""
        color = _ON[light] if on else _OFF[light]
        self.canvas.itemconfig(self.light_ids[frame][light], fill=color)

    def set_frame(self, frame: int, light: int) -> None:
        """Light exactly one light in a frame; dim the other two."""
        for li in range(3):
            self.set_light(frame, li, li == light)
