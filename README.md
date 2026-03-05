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

## Controls

| Control | Action |
|---|---|
| SW1/SW2 slider (panel) | Toggle between main route and siding (2-second transition) |

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

| Block | Location | Speed |
|---|---|---|
| BL1 | Left semicircle | 150 |
| BL2 | Bottom main straight (SW1 → SW2) | 300 |
| BL3 | Siding U-shape below bottom straight | 75 |
| BL4 | Right semicircle | 150 |
| BL5 | Top straight | 300 |

## Signals

Three two-frame signals are placed at the switch areas. Each signal has a top head (movement aspect) and a bottom head (route/switch aspect).

| Signal | Location | Top head | Bottom head |
|---|---|---|---|
| SG1 | Left switch area | Mirrors bottom head | Switch state |
| SG2 | Right switch area | Green=straight, Red=transition or diverge | Switch state |
| SG3 | Siding right end (flip) | Red=straight or transition, Yellow=diverge | Switch state |

**Bottom head (all signals):** Green = main route, Red = transition (2 s), Yellow = siding.

## Trains

Two trains run simultaneously. Train 1 starts near SW2 (BL4); Train 2 starts at the centre of BL5. Speed is set automatically by block. Current block and speed for each train are shown in the top-left of the canvas.

## Project Structure

| File | Description |
|---|---|
| `main.py` | App entry point — tkinter window, canvas, 60 fps animation loop, signal/switch logic |
| `track.py` | `Segment` (polyline + parametric position/angle), `Track` builder, `block_ranges` |
| `train.py` | `Train` — speed, route selection, block detection |
| `signals.py` | `Signal` — two-frame, three-light railway signal widget |
