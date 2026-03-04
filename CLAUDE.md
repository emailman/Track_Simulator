# Track Simulator — Claude Instructions

## Running the project

```bash
python main.py
```

Virtual env: `.venv/` (Python 3.14). No external dependencies — stdlib only (tkinter, math, time).

## Architecture

| File | Responsibility |
|---|---|
| `main.py` | `App` — tkinter root, 800×500 canvas, 60 fps loop via `root.after` |
| `track.py` | `Segment` (polyline + arc-length parametric lookup), `Track` (segment graph builder) |
| `train.py` | `Train` — moves along segment graph, selects route at junctions, reports current block |
| `signals.py` | `Signal` — two-frame, three-light signal drawn on canvas |

## Track layout

- Main loop: rounded rectangle (stadium shape), **clockwise on screen**
- Left end centre `(140, 200)`, right end centre `(660, 200)`, end-radius = 80
- Top straight (BL5): `y=120`; Bottom straight (BL2): `y=280`
- `sw1=(220,280)` near left end; `sw2=(580,280)` near right end
- **seg0** — long way round: `sw2 → right semicircle (BL4) → top (BL5) → left semicircle (BL1) → sw1`; `next=[seg1, seg2]`
- **seg1** — bottom straight BL2: `sw1→sw2`; `next=[seg0]`
- **seg2** — siding BL3 (U-shape below bottom straight): `sw1→sw2`; `next=[seg0]`

Block ranges on seg0 are computed by `Segment.t_near()` against the top-straight boundary points `(580,120)` and `(220,120)`.

## Key design decisions

- Polyline segments with cumulative arc-length lookup for accurate `position_at(t)`
- Train orientation from `angle_at(t)` via 2-point finite difference
- Train sprite is a rotated polygon (deleted and recreated each frame)
- Switch choice: `seg0.next[0]` = main (seg1), `seg0.next[1]` = siding (seg2)
- `Track.block_ranges` dict: `name → (segment, t0, t1)`; set dynamically on the instance after graph wiring

## Conventions

- Coordinate system: canvas pixels, origin top-left, y increases downward
- `t` parameter: `0.0` = segment start, `1.0` = segment end
- Speed unit: canvas pixels per second
- Frame budget: ~16 ms (60 fps); keep per-frame work O(segments) or less
