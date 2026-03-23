# Architecture Overview

2048Py is a roguelike 2048 game split into two layers:

- **C++ engine** (`src/engine/`) — deterministic game logic compiled as a Python extension via pybind11
- **Python frontend** (`src/main.py`, `src/functions.py`) — rendering (Pygame + ModernGL CRT shader), animation, UI

```
┌─────────────────────────────────────────┐
│              Python Frontend            │
│  main.py (game loop, event handling)    │
│  functions.py (rendering, animation)    │
└────────────────┬────────────────────────┘
                 │  pybind11 (.so)
┌────────────────▼────────────────────────┐
│            C++ Engine                   │
│  GameEngine → Board → Tile              │
│  TileBehavior dispatch                  │
│  movement::move_* (segment-based)       │
│  PassiveRoller, SlowMoverState          │
└─────────────────────────────────────────┘
```

## Directory Structure

```
2048Py/
├── compile.sh / compile.bat   # Build scripts
├── src/
│   ├── main.py                # Game loop, OpenGL setup, event handling
│   ├── functions.py           # All drawing, animation, and helper functions
│   ├── game2048_engine*.so    # Compiled C++ module (placed here after build)
│   ├── assets/
│   │   ├── fonts/             # pixelOperatorBold.ttf
│   │   └── sprites/           # bomb.png, snailBody.png, snailShell.png
│   └── engine/                # C++ source
│       ├── CMakeLists.txt
│       ├── include/           # Headers
│       └── src/               # Implementation + pybind11 bindings
└── docs/                      # This documentation
```

## Data Flow Per Turn

1. Player presses an arrow key in `main.py`
2. `func.process_move(g, direction)` is called
3. `g.engine.process_move(direction)` runs the C++ 8-phase turn processor
4. Returns a `TurnResult` containing all mutations (moves, merges, spawns, etc.)
5. Python unpacks `TurnResult` into animation queues (`g.moving_tiles`, `g.merging_tiles`, etc.)
6. `sync_grid_from_engine(g)` copies the new board state to `g.playingGrid`
7. `update_animations(g, dt)` drives the 3-phase animation each frame

## Turn Phases (C++ side)

| # | Phase | Description |
|---|-------|-------------|
| 1 | Pre-snapshot | Behaviors capture pre-move positions |
| 2 | Frozen-set build | Behavior-owned, user-frozen, snails, walls added to frozen set |
| 3 | Pre-bomb detonation | Bombs adjacent to frozen tiles explode |
| 4 | Regular movement | Non-frozen tiles slide and merge |
| 5 | Post-bomb detonation | Bombs newly adjacent to frozen tiles explode |
| 6 | Slow mover advance | Previously-tracked slow tiles step 1 cell |
| 7 | Behavior advances | Each `TileBehavior::advance()` called in registration order |
| 8 | Snail advancement | Snails move randomly (only on valid turns) |

## Animation Phases (Python side)

| Phase | Content |
|-------|---------|
| 1 | Regular tile movement and merges |
| 2 | Snail movements |
| 3 | Slow/contrarian tile advances |

Phases run sequentially; each waits for the previous to finish before starting.

## Global State (`g`)

All mutable game state lives in the `G()` instance (`g`) in `main.py`:

| Attribute | Type | Description |
|-----------|------|-------------|
| `g.engine` | `GameEngine` | C++ engine instance |
| `g.playingGrid` | `numpy.ndarray` | Current board values (copy of engine state) |
| `g.points` | `int` | Current score |
| `g.rows`, `g.cols` | `int` | Board dimensions |
| `g.passive_map` | `dict[tuple, int]` | `(r,c) → passive bitmask` |
| `g.pending_passives` | `list` | Queue of passive candidates to show in menu |
| `g.abilities` | `list[dict]` | Ability definitions (name, cost, charges) |
| `g.frozen_tiles` | `set` | User-frozen tile positions |
| `g.animating` | `bool` | Whether an animation is in progress |
| `g.current_move_phase` | `int` | Active animation phase (1, 2, or 3) |
