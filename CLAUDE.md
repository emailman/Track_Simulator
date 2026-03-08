# Track Simulator — Claude Instructions

## Running the project

```bash
python main.py
```

Virtual env: `.venv/` (Python 3.14). No external dependencies — stdlib only (tkinter, math, time).

## Architecture

| File | Responsibility |
|---|---|
| `main.py` | `App` — tkinter root, 800×500 canvas, 60 fps loop via `root.after`, switch/signal/speed/automation logic |
| `track.py` | `Segment` (polyline + arc-length parametric lookup), `Track` (segment graph builder, `block_ranges`) |
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

## Block speeds

```python
BLOCK_SPEEDS = {"BL1": 150, "BL2": 75, "BL3": 75, "BL4": 150, "BL5": 300}
```

Speed is applied automatically each frame in `_loop` after `current_block()` is called. There are no manual speed controls.

## Trains

- **T1 (blue)** — starts at centre of BL4
- **T2 (orange)** — starts at centre of BL1
- Route label shows `Route: BL2` (SW1 straight) or `Route: BL3` (SW1 diverge)

## Switches

SW1 and SW2 are controlled **independently and automatically** — there is no manual slider.

- **SW1** (diverging junction at sw1): controls which path trains take from seg0. Sets `train.route` / `train2.route`. Transition: 1 s.
- **SW2** (converging junction at sw2): visual/signal state only — does not affect routing. Transition: 1 s.
- `_set_sw1(route)` — sets SW1, starts `_switch_transition_end` timer, updates SG1
- `_set_sw2(route)` — sets `_sw2_state`, starts `_sw2_transition_end` timer, updates SG2/SG3

## Automatic rules (evaluated each frame in `_loop`)

| Trigger | Action |
|---|---|
| Orange (T2) enters BL1 | SW1 → straight (BL2 route) |
| Blue (T1) enters BL1 | SW1 → diverge (BL3 route) |
| Orange reaches centre of BL2 | Stop 3 s, then SW2 → straight; held until SW2 indicator is green (held longer if blue is in BL4) |
| Blue reaches centre of BL3 | Stop 3 s, then SW2 → diverge; held until SW2 indicator is yellow (held longer if orange is in BL4) |
| BL1 occupied when second train arrives | Trailing train held at BL1 entry; released when BL1 clears |
| BL4 occupied when second train arrives | Trailing train held at BL4 entry; released when BL4 clears |

**BL4 resume rule:** a train stopped at its timed stop (BL2 or BL3 centre) will not resume as long as the other train occupies BL4.

**SW2 indicator rule:** after the timed stop and BL4 clear, the train calls `_set_sw2` once (guarded by `_train2_waiting_sw2_green` / `_train_waiting_sw2_yellow`) and remains stopped until `_sw2_state` matches the expected route **and** `_sw2_transition_end == 0`.

## Signals

Three signals: SG1 (left switch, x=190,y=280), SG2 (right switch, x=550,y=280), SG3 (siding right end, x=505,y=363, flip=True).

Each signal has two frames (top=frame 0, bottom=frame 1). `_update_signal_switch_indicators()` drives both frames whenever switch state changes or transition ends.

**SG1 reflects SW1; SG2 and SG3 reflect SW2.**

**Bottom head:** Green=straight, Red=transition, Yellow=diverge.

**Top head per signal:**

| Signal | Green bottom | Red bottom | Yellow bottom |
|---|---|---|---|
| SG1 | Green | Red | Yellow |
| SG2 | Green | Red | Red |
| SG3 | Red | Red | Yellow |

## Switch transition

- `_switch_transition_end: float` — SW1 `perf_counter()` deadline; `0.0` when stable
- `_sw2_transition_end: float` — SW2 `perf_counter()` deadline; `0.0` when stable
- On change: set to `now + 1.0`, marker goes red, signals go red
- In `_loop`: when deadline passes, clear to `0.0`, call `_update_switch_markers()` and `_update_signal_switch_indicators()`

## Key design decisions

- Polyline segments with cumulative arc-length lookup for accurate `position_at(t)`
- Train orientation from `angle_at(t)` via 2-point finite difference
- Train sprite is a rotated polygon (deleted and recreated each frame)
- Switch choice: `seg0.next[0]` = main (seg1/BL2), `seg0.next[1]` = siding (seg2/BL3)
- `Track.block_ranges` dict declared in `Track.__init__` as `dict[str, tuple[Segment, float, float]]`
- BL1/BL4 mutual exclusion: trailing train's `t` is clamped to `_bl1_t0` / `_bl4_t0` while held

## Conventions

- Coordinate system: canvas pixels, origin top-left, y increases downward
- `t` parameter: `0.0` = segment start, `1.0` = segment end
- Speed unit: canvas pixels per second
- Frame budget: ~16 ms (60 fps); keep per-frame work O(segments) or less
- Use string literals for tkinter geometry args (`"left"`, `"vertical"`, `"y"`) not `tk.LEFT` etc. — avoids PyCharm `Literal` warnings
