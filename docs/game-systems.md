# Game Systems

## Passive System

Passives are bitmask flags assigned to numbered tiles. A tile can hold multiple passives simultaneously (OR of flags).

### Available Passives

| Passive | Bitmask | Behavior |
|---------|---------|---------|
| `NONE` | 0 | Standard tile |
| `A_LITTLE_SLOW` | 1 | Tile moves 1 cell/turn; frozen during the player's regular move phase |
| `CONTRARIAN` | 2 | Tile moves in the direction opposite to the player's input |
| Slow Contrarian | 3 | Both flags set; moves 1 cell/turn in the opposite direction |

A merged tile carries the **OR of both source tiles' passives**, in every merge path (regular compaction, behind-merges, contrarian merges, slow-mover arrivals). Merging a Slow tile with a Contrarian tile is how Slow Contrarian arises — the passive menu only ever targets passive-free tiles.

### How Passives Are Assigned

After each turn, `PassiveRoller::roll()` rolls once per merge:

- **Roll chance** = `merge_value × 0.1%` (e.g., 512 → 51.2%; values ≥ 1000 grant a guaranteed success plus a roll on the remainder)
- On success, a **random eligible tile** becomes the `PassiveCandidate` — eligible means numbered, passive-free, and not a merge destination, the spawned tile, a slow mover, or a snail
- At most one candidate per turn: rolling stops at the first success
- Python queues candidates and shows a selection menu overlay after animations complete; the player picks one passive for the candidate tile

### Passive Indicator (Visual)

`draw_passive_indicator(g, r, c)` reads `g.passive_map[(r,c)]`:

- **Green dot** = A_LITTLE_SLOW bit is set
- **Red dot** = CONTRARIAN bit is set
- Both dots shown for combined passive (bitmask = 3)

### Slow Tile Behavior Detail

When a slow tile moves:

1. It is **frozen** during the regular move phase (other tiles compact around it).
2. If a matching tile compacts directly behind it, a **behind-merge** happens first (before the slow tile steps).
3. The slow tile then moves exactly **1 cell** in the player's direction.
4. Regular tiles **cascade fill** into the cell it vacated.
5. If the slow tile's destination is more than 1 cell away, a `SlowMoverState` is created to track the remaining travel across subsequent turns.

### Contrarian Tile Behavior Detail

1. Contrarian tiles are **frozen** during regular move.
2. After regular move, they slide in the **opposite** direction.
3. **Pure contrarian**: slides all the way to the far wall or a merge target.
4. **Slow contrarian** (both flags): slides 1 cell/turn in the opposite direction; `SlowMoverState` created if destination > 1 cell away.
5. Leading-edge tiles are processed first to prevent chained pushes.

---

## Ability System

### Available Abilities

| Ability | Index | Base Cost | Description |
|---------|-------|-----------|-------------|
| Bomb | 0 | 500 pts | Place a bomb tile; destroys an adjacent tile when it moves |
| Freeze | 1 | 750 pts | Lock a tile in place for one turn |
| Switch | 2 | 1550 pts | Swap two tiles (animated fade) |

Abilities are defined in `g.abilities` as a list of dicts `{name, cost, charges, description}`.

### Using an Ability

1. Click the ability button (active charges required; button grayed out otherwise).
2. Button enters selection mode — click a grid tile to place/apply.
3. ESC cancels selection.

**Switch** is two-step: click source tile, then destination tile.

**Switch restrictions**: Only once per turn (`g.switch_used_this_turn`). The flag resets in `process_move()` on a valid move.

### Bomb Mechanics

- Placed on an empty cell; value = -1.
- During movement, a bomb destroys the first tile it collides with in the slide direction; **the bomb is consumed with it** at the landing cell.
- A bomb with nothing to hit (last in its segment) just slides like a normal tile.
- Destruction creates a particle explosion.
- **Two detonation windows per turn** (pre-movement and post-movement) cover bombs adjacent to frozen tiles.

### Freeze Mechanics

- A frozen tile is immovable for one full turn.
- Frozen tiles are stored in `g.frozen_tiles` (Python) and passed to `g.engine.place_freeze(r, c)`.
- Frozen tiles show a visual overlay (semi-transparent blue).
- Freeze is **cleared automatically** after a valid turn: the engine clears its frozen set inside `process_move` (C++), and Python clears its overlay set `g.frozen_tiles` in `func.process_move`. Invalid turns leave freezes in place.

---

## Ability Shop

- Accessible via a shop button in the sidebar.
- Each row shows an ability's name, cost, and current charges.
- Purchasing deducts points and increments `charges`.
- Shop auto-scales its height to `len(g.abilities)` rows (80 px each).

### Price Scaling

Prices increase with each board expansion:

| Expansion # | Multiplier |
|-------------|-----------|
| 1st | ×5 |
| 2nd | ×2.5 |
| 3rd+ | ×2.05 |

`start_grid_expansion(g)` applies the multiplier to all abilities' costs.

---

## Board Expansion

The board grows when a merge **produces a tile equal to `tar_expand`** (2048, 4096, 8192, … — doubles after each expansion). Merges from any phase count: regular, behavior-phase, and slow-mover arrivals.

1. `TurnResult.should_expand` is `True`.
2. Python calls `start_grid_expansion(g)`, which determines the expand direction and calls `g.engine.complete_expansion(direction)`.
3. The C++ engine adds a row or column; updates all slow mover and snail positions.
4. Python animates the expansion (`g.grid_expanding`, `g.expand_progress`).
5. Shop prices are scaled up.
6. Color scheme may transition to the next theme.

---

## Snail Tiles

Snail tiles (value = -2) are special moving obstacles:

- Displayed as a composite sprite (body + shell) with animated color cycling.
- Move **randomly** after regular and slow-tile phases each turn.
- Movement logged in `TurnResult.random_mover_updates`.
- Snails block regular tile compaction (they are part of the frozen set during regular movement).
- Snails can be killed by adjacent bombs (`TurnResult.snail_bomb_kills`).

---

## Wall Tiles

Wall tiles (value = -3) are permanent obstacles:

- Cannot move, merge, or be destroyed by normal means.
- Always in the frozen set, acting as fixed barriers for compaction segments.

---

## Scoring

- Points accumulate from merges: merging two tiles of value `n` grants `2n` points.
- **Every merge scores**, whichever phase performs it — regular compaction, slow/contrarian behavior merges, and slow-mover arrival merges all contribute to `points_gained`.
- Starting score: **4500**.
- Points are spent in the ability shop.

---

## Move Validity

A turn is only valid if `TurnResult.board_changed` is `True`. This requires at least one tile to have moved or merged during regular movement. Snail movement alone does **not** count as a valid turn.

Invalid turns do not:
- Consume ability uses
- Roll for passives
- Spawn new tiles
- Advance snails
