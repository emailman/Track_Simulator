# Track Simulator

A Python/tkinter visual train simulator featuring an oval main loop with a passing siding.

![Track Simulator screenshot](screenshot.png)

## Requirements

- Python 3.14+
- tkinter (included in the standard library)

## Running

```bash
python main.py
```

There are no manual controls — all switch and speed changes are fully automatic.

## Track Layout

The track is a rounded rectangle (stadium shape) with a passing siding below the bottom straight.

```
        BL5 (top straight)
    ┌──────────────────────────┐
BL1 │                          │ BL4
    └──SW1──────────────SW2────┘
        BL2 (bottom straight)
        SW1──BL3 (siding)──SW2
```

**Block speeds:**

| Block | Location | Speed (px/s) |
|---|---|---|
| BL1 | Left semicircle | 150 |
| BL2 | Bottom main straight (SW1 → SW2) | 75 |
| BL3 | Siding U-shape below bottom straight | 75 |
| BL4 | Right semicircle | 150 |
| BL5 | Top straight | 300 |

## Trains

Two trains run simultaneously:

- **T1 (blue)** — starts at the centre of BL4
- **T2 (orange)** — starts at the centre of BL1

Current block and speed for each train are shown in the top-left of the canvas.

## Automatic Switch Rules

Switches SW1 and SW2 are controlled independently by automation rules.

**SW1** (diverging junction — controls which route trains take):

| Trigger | Action |
|---|---|
| Orange (T2) enters BL1 | SW1 → straight → trains route via BL2 |
| Blue (T1) enters BL1 | SW1 → diverge → trains route via BL3 |

**SW2** (converging junction — visual/signal indicator):

| Trigger | Action |
|---|---|
| Orange stops at centre of BL2 (3 s) | After stop: SW2 → straight |
| Blue stops at centre of BL3 (3 s) | After stop: SW2 → diverge |

A stopped train will not resume until its 3-second timer has expired **and** the other train has cleared BL4.

## Block Occupancy Rules

- **BL1** — only one train at a time. The trailing train is held at the BL1 entry until the section clears.
- **BL4** — only one train at a time. The trailing train is held at the BL4 entry until the section clears.

## Signals

Three two-frame signals are placed at the switch areas. Each signal has a top head (movement aspect) and a bottom head (route/switch aspect). Switch transitions take 1 second, during which signals show red.

| Signal | Location | Reflects |
|---|---|---|
| SG1 | Left switch area (x=190, y=280) | SW1 state |
| SG2 | Right switch area (x=550, y=280) | SW2 state |
| SG3 | Siding right end (x=505, y=363, flipped) | SW2 state |

**Bottom head:** Green = straight, Red = transition, Yellow = diverge.

**Top head mapping:**

| Signal | Green bottom | Red bottom | Yellow bottom |
|---|---|---|---|
| SG1 | Green | Red | Yellow |
| SG2 | Green | Red | Red |
| SG3 | Red | Red | Yellow |

## Project Structure

| File | Description |
|---|---|
| `main.py` | App entry point — tkinter window, canvas, 60 fps animation loop, automatic switch/signal/speed logic |
| `track.py` | `Segment` (polyline + parametric position/angle), `Track` builder, `block_ranges` |
| `train.py` | `Train` — speed, route selection, block detection |
| `signals.py` | `Signal` — two-frame, three-light railway signal widget |
