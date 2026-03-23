# Python Frontend

The frontend is split between two files:

| File | Responsibility |
|------|---------------|
| `src/main.py` | Game loop, OpenGL/Pygame setup, event handling, top-level rendering |
| `src/functions.py` | All drawing functions, animation logic, color schemes, CRT shader |

---

## main.py

### Setup

1. Pygame + ModernGL are initialized in fullscreen or windowed mode.
2. A high-resolution offscreen surface (`render_surface`, 3840×2400) is created for Pygame drawing.
3. A fullscreen OpenGL quad renders that surface through the CRT shader each frame.

**Resolution config** — set these in `main.py` to match your display:

```python
NATIVE_WIDTH  = 2560   # Your screen width
NATIVE_HEIGHT = 1600   # Your screen height
```

### Game State (`G()`)

All mutable state lives in a single `G()` instance named `g`. Key attributes:

#### Display
| Attribute | Type | Description |
|-----------|------|-------------|
| `g.screen` | `pygame.Surface` | Window surface |
| `g.render_surface` | `pygame.Surface` | Offscreen Pygame canvas (3840×2400) |
| `g.ctx` | `moderngl.Context` | OpenGL context |
| `g.is_fullscreen` | `bool` | Current display mode |

#### Board
| Attribute | Type | Description |
|-----------|------|-------------|
| `g.engine` | `GameEngine` | C++ engine instance |
| `g.playingGrid` | `numpy.ndarray` | Board values (synced from engine) |
| `g.rows`, `g.cols` | `int` | Board dimensions |
| `g.points` | `int` | Score |
| `g.passive_map` | `dict` | `(r,c) → passive bitmask int` |
| `g.pending_passives` | `list` | Queue of passive candidates |
| `g.frozen_tiles` | `set` | User-frozen tile positions |

#### Animations
| Attribute | Description |
|-----------|-------------|
| `g.animating` | `True` while any animation is running |
| `g.animation_progress` | `0.0–1.0` progress for current phase |
| `g.current_move_phase` | `1` = regular, `2` = snails, `3` = slow tiles |
| `g.moving_tiles` | List of `(from_r, from_c, to_r, to_c, value)` |
| `g.merging_tiles` | List of `(from_r, from_c, into_r, into_c, result_value)` |
| `g.new_tile_pos` | `(r, c)` of newly spawned tile |
| `g.grid_expanding` | `True` during board expansion animation |

#### Abilities
| Attribute | Description |
|-----------|-------------|
| `g.abilities` | `list[dict]` — `{name, cost, charges, description}` |
| `g.selecting_bomb_position` | Awaiting tile click to place bomb |
| `g.selecting_freeze_position` | Awaiting tile click to freeze |
| `g.selecting_switch_position` | `False` / `"first"` / `"second"` |
| `g.switch_source` | `(r, c)` of first selected tile for switch |
| `g.switch_used_this_turn` | Blocks switch button after use |

### Event Loop

```
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        # Passive menu: consumes all input when open
        # Shop: consumes all input when open
        # Arrow keys → func.process_move(g, direction)
        # F11 → toggle fullscreen
        # ESC → cancel ability or quit

    func.update_animations(g, dt)
    func.update_color_transition(g)

    # Draw background, grid, tiles, particles, UI panels
    # Render via OpenGL CRT shader
    pygame.display.flip()
```

Input is blocked during animations (`g.animating == True`) and while overlays (passive menu, shop) are open.

---

## functions.py

### Color Schemes

Four themes switch automatically based on the `tar_expand` milestone:

| Threshold | Theme |
|-----------|-------|
| 2048 | GRUVBOX |
| 4096 | NORD |
| 8192 | SCARY_FOREST |
| 16384+ | TOKYO_NIGHT |

Transitions are smooth (linear interpolation with `ease_out_cubic`). The active palette is interpolated into `g.colors` each frame by `update_color_transition(g)`.

### Animation Helpers

```python
lerp(start, end, t)          # Linear interpolation
ease_out_cubic(t)            # Smooth deceleration easing
lerp_color(c1, c2, t)        # RGB tuple interpolation
```

### process_move(g, direction)

Called from `main.py` on each valid keypress:

1. Calls `g.engine.process_move(direction)` → `TurnResult`
2. If `board_changed` is `False`, returns immediately (invalid move)
3. Unpacks `TurnResult` into animation queues
4. Calls `sync_grid_from_engine(g)` to refresh `g.playingGrid` and `g.passive_map`
5. Queues pending passives from `result.passive_candidates`
6. Triggers expansion animation if `result.should_expand`
7. Sets `g.animating = True`, `g.current_move_phase = 1`

### update_animations(g, dt)

Runs every frame while `g.animating`:

- Advances `g.animation_progress` by `dt * ANIMATION_SPEED`
- **Phase 1** (regular moves): interpolates tile positions; on completion triggers merge bounce, then starts Phase 2 if snails moved
- **Phase 2** (snails): interpolates snail positions; on completion starts Phase 3 if slow tiles moved
- **Phase 3** (slow tiles): interpolates slow/contrarian tile positions
- On final phase completion: opens passive menu if `g.pending_passives` is non-empty, or expansion overlay if `g.grid_expanding`

### sync_grid_from_engine(g)

```python
def sync_grid_from_engine(g):
    flat = g.engine.get_grid_values()      # C++ → flat int list
    g.playingGrid = np.array(flat).reshape(g.rows, g.cols)
    g.passive_map = {(r, c): pt for r, c, pt in g.engine.get_passive_map()}
    g.points = g.engine.score()
```

### Drawing Functions

| Function | Description |
|----------|-------------|
| `draw_tile(g, r, c, value, ...)` | Render one grid cell, with optional scale override |
| `prepare_tile_surface(g, value, scale)` | Return a cached scaled surface for a tile value |
| `draw_snail_tile(g, x, y, size)` | Render the composite snail sprite (body + shell) |
| `draw_passive_indicator(g, r, c)` | Draw colored dots for passive bitmask |
| `draw_button(g, x, y, w, h, text, ...)` | Ability button with active/disabled states |
| `draw_shop(g)` | Modal shop overlay |
| `draw_passive_menu(g)` | Modal passive selection overlay |
| `draw_game_over(g)` | Final score screen |
| `draw_move_order_chart(g)` | Phase animation diagram in the sidebar |

### Ability Layout

```python
ability_button_layout(g)   # Returns left_x, mid_x, right_x for the 3 buttons
```

Buttons are drawn at fixed vertical positions; the shop auto-scales to `len(g.abilities)` rows (80 px each, starting at `panel_y + 130`).

### Particle System

```python
class Particle:      # Physics: position, velocity, gravity, decay, color
class ParticleSystem # Manages list of Particle; update() + draw()
```

Bomb detonations spawn 30–40 particles that fan outward and fade.

### CRT Shader

`render_to_opengl(g)` copies the Pygame surface to an OpenGL texture and renders it through a GLSL CRT emulation shader:

- **Features**: Scanlines, bloom, barrel distortion, shadow mask, brightness control
- **Key uniforms**: `hardScan`, `hardPix`, `warpX`, `warpY`, `maskDark`, `maskLight`
- Rendered on a fullscreen quad via a VAO

---

## Rendering Pipeline (per frame)

```
Pygame drawing on g.render_surface
        ↓
render_to_opengl(g):
    copy surface pixels → OpenGL texture
    bind texture, set shader uniforms
    draw fullscreen quad through CRT shader
        ↓
pygame.display.flip()
```

---

## Tile Cache

`prepare_tile_surface` caches pre-scaled Pygame surfaces keyed by `(value, scale_int)`. This avoids redrawing text/colors for unchanged tiles every frame.
