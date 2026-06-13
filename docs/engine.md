# C++ Engine

The engine lives in `src/engine/` and is compiled to `game2048_engine*.so` via pybind11.

## Headers (`include/`)

| Header | Purpose |
|--------|---------|
| `game_engine.h` | `GameEngine` class — top-level API |
| `board.h` | `Board` — 2D grid of `Tile` objects |
| `tile.h` | `Tile` — value + passive bitmask |
| `passive.h` | `PassiveType` enum and bitmask helpers |
| `tile_behavior.h` | `TileBehavior` abstract base; `MoveContext` |
| `movement.h` | `movement::move_*` functions + `MoveResult` |
| `turn_result.h` | `TurnResult` — mutation log returned to Python |
| `slow_mover.h` | `SlowMoverState` — per-tile slow tracking |
| `slow_behavior.h` | `SlowBehavior` — pure A_LITTLE_SLOW implementation |
| `contrarian_behavior.h` | `ContrarianBehavior` — pure + combined CONTRARIAN |
| `passive_roller.h` | `PassiveRoller` — probability-based passive rolling |
| `random_mover.h` | `RandomMoverState` — snail position tracking |

---

## GameEngine

**File**: `game_engine.h` / `game_engine.cpp`

### Constructors

```cpp
GameEngine(int rows, int cols)                     // random seed
GameEngine(int rows, int cols, unsigned int seed)  // deterministic
```

Initializes the board, registers behaviors (SlowBehavior then ContrarianBehavior), spawns 2 starting tiles. Initial score is 4500, initial `tar_expand` is 2048.

The seeded variant derives all RNGs (board spawns, passive rolls, snail movement) from one seed: same seed + same call sequence = identical runs. The test harness (`tests/`) is built on it.

### Core Method

```cpp
TurnResult process_move(const std::string& direction)
// direction: "left" | "right" | "up" | "down"
```

Runs the 8-phase turn and returns a `TurnResult` with all mutations.

### Ability Methods

```cpp
void place_bomb(int r, int c)         // Place a bomb tile (-1) at position
void place_freeze(int r, int c)       // Add to user-frozen set
void clear_freeze(int r, int c)       // Remove from user-frozen set
void switch_tiles(int r1, int c1, int r2, int c2)  // Swap two tiles
void complete_expansion(const std::string& direction) // Expand the board
```

### Query Methods

```cpp
std::vector<int>   get_grid_values()  // Flat row-major array of tile values
std::vector<...>   get_passive_map()  // (row, col, passive_type) tuples
std::vector<...>   get_slow_movers()  // SlowMoverState list
std::vector<...>   get_random_movers()// RandomMoverState list
int  score()
int  tar_expand()                     // Next expansion threshold
int  rows(), cols()
bool has_moves()
```

---

## Board

**File**: `board.h` / `board.cpp`

The `Board` owns a 2D `std::vector<std::vector<Tile>>`.

### Key Methods

```cpp
Tile& at(int r, int c)                         // Mutable tile access
void expand(const std::string& direction)      // Add a row or column
std::pair<int,int> spawn_number(excluded_set)  // Spawn a 2 in a random empty cell
std::pair<int,int> spawn_bomb()
std::pair<int,int> spawn_snail()
std::pair<int,int> spawn_wall()
std::vector<std::pair<int,int>> empty_cells(excluded)
std::vector<std::pair<int,int>> occupied_numbered_cells(excluded)
std::vector<int>   to_flat_values()            // Serialize for Python
```

### Special Tile Values

| Value | Meaning |
|-------|---------|
| 0 | Empty cell |
| -1 | Bomb |
| -2 | Snail |
| -3 | Wall |
| 2, 4, 8, … | Normal numbered tile |

---

## Tile

**File**: `tile.h`

```cpp
struct Tile {
    int value;           // 0=empty, -1=bomb, -2=snail, -3=wall, else power-of-2
    PassiveType passive; // Bitmask of passive flags
};
```

---

## Passives

**File**: `passive.h`

```cpp
enum class PassiveType : int {
    NONE         = 0,
    A_LITTLE_SLOW = 1,   // Tile moves 1 cell/turn, frozen during regular move
    CONTRARIAN   = 2,    // Tile moves in the opposite player direction
};

bool has_passive(PassiveType stored, PassiveType flag); // Bitwise AND check
```

Passives are bitmasks. A tile can hold both (value `3` = slow + contrarian = "Slow Contrarian").

---

## Movement

**File**: `movement.h` / `movement.cpp`

Movement splits rows/columns into **segments** divided by frozen tiles. Each segment is compacted independently, then results are merged back.

```cpp
MoveResult move_left (Board&, const frozen_set&)
MoveResult move_right(Board&, const frozen_set&)
MoveResult move_up   (Board&, const frozen_set&)
MoveResult move_down (Board&, const frozen_set&)
```

### MoveResult

```cpp
struct MoveResult {
    std::vector<MoveInfo>  moves;         // (from_r, from_c, to_r, to_c, value)
    std::vector<MergeInfo> merges;        // (from_r, from_c, into_r, into_c, result_value)
    std::set<...>          bomb_destroyed;// Cells destroyed by bombs
    bool                   board_changed;
};
```

### Bomb Mechanics

- A bomb tile (-1) destroys the next tile in the compaction direction; the bomb is consumed with it.
- A bomb that is last in its segment (nothing to hit) slides like a normal tile.
- Destroyed positions are logged in `bomb_destroyed` (the landing cell).

### Merging Rules

- Two tiles of equal value merge into a doubled tile.
- The merged tile carries the **OR of both sources' passives** (`combine_passives` in `passive.h`). This rule applies in every merge path engine-wide: segment merges, behind-merges, contrarian merges, slow-mover arrivals, and frozen-slow-mover merges.
- Multiple merges per segment are allowed (e.g., `2 2 2 2` → `4 4` → `8`).
- Every merge awards its doubled value as points, regardless of which phase performs it.

---

## TileBehavior (Abstract)

**File**: `tile_behavior.h`

All passive behaviors implement this interface:

```cpp
class TileBehavior {
public:
    virtual bool matches(PassiveType p) = 0;
    virtual bool freeze_during_move() = 0;      // Freeze tile during regular move?
    virtual bool freeze_tile_behind() = 0;       // Also freeze same-value tile behind?
    virtual void pre_snapshot(Board&, ...) {}    // Capture pre-move positions
    virtual bool advance(MoveContext&, TurnResult&) = 0; // Execute behavior phase
    virtual bool blocks_cascade() = 0;           // Stop cascade fill at this tile?
    virtual bool requires_slow_mover_cleanup(PassiveType) = 0;
};
```

### MoveContext

Bundles mutable state passed to `advance()`:

```cpp
struct MoveContext {
    Board& board;
    std::string direction;
    std::vector<std::unique_ptr<TileBehavior>>& behaviors;
    std::vector<SlowMoverState>& slow_movers;
    std::set<std::pair<int,int>>& user_frozen;
    // ...
};
```

### Registration

Behaviors are registered in the `GameEngine` constructor:

```cpp
behaviors_.push_back(std::make_unique<SlowBehavior>());
behaviors_.push_back(std::make_unique<ContrarianBehavior>());
```

**Registration order = advance order.** First-match-wins for tile ownership.

---

## SlowBehavior

**File**: `slow_behavior.h` / `slow_behavior.cpp`

Handles tiles with **pure A_LITTLE_SLOW** (no CONTRARIAN bit).

**Behavior during `advance()`**:
1. **Behind-merge**: A regular tile may have compacted next to a frozen slow tile during the regular move phase — merge it now. (If the absorbed tile carried CONTRARIAN, the merged tile changes owner and stays put until next turn.)
2. **Scan ahead**: Find ultimate destination (empty cells, then first non-slow numbered tile).
3. **Move 1 cell**: If destination is 1 cell away and enables a merge, do it immediately. Otherwise create a `SlowMoverState` for remainder of travel.
4. **Cascade fill**: Regular tiles slide into the vacated cell.
5. **Frozen slow-mover merge**: If a slow mover is in the user-frozen set and a matching regular tile is behind it, merge them.

---

## ContrarianBehavior

**File**: `contrarian_behavior.h` / `contrarian_behavior.cpp`

Handles tiles with **any CONTRARIAN bit** (pure or combined with slow).

**Behavior during `advance()`**:
1. **Pre-snapshot**: Record positions; pre-compute which tiles are immediately blocked.
2. Process leading-edge tiles first (to avoid chain reactions).
3. Skip blocked tiles.
4. **Scan opposite direction**: Find a merge target or the farthest empty cell.
5. **Move**:
   - Pure CONTRARIAN: slide fully to destination.
   - Slow + CONTRARIAN: move 1 cell; create `SlowMoverState` if destination > 1 cell away.
6. **Cascade fill** on vacated cell.

---

## SlowMoverState

**File**: `slow_mover.h`

Tracks a tile that moves 1 cell per turn:

```cpp
struct SlowMoverState {
    int current_row, current_col;  // Current position
    int dest_row, dest_col;        // Final destination
    int dr, dc;                    // Step direction per turn (-1, 0, 1)
    int value;
    PassiveType passive;
    bool active;
};
```

Created by behavior `advance()` when a tile has more than 1 cell to travel. Consumed by `advance_slow_movers()` each turn.

---

## PassiveRoller

**File**: `passive_roller.h` / `passive_roller.cpp`

After each turn, `PassiveRoller::roll()` rolls once per merge:

- **Chance** = `merge_value × 0.1%` (e.g., 512 → 51.2%; values ≥ 1000 add guaranteed successes plus a roll on the remainder).
- On success, one **random eligible tile** becomes the `PassiveCandidate` — eligible means numbered, passive-free, and not a merge destination, the spawned tile, a slow mover, or a snail.
- At most one candidate per turn: rolling stops at the first success.
- Python displays a selection menu for the candidate.

---

## TurnResult

**File**: `turn_result.h`

Returned by `process_move()`. Python uses this to drive animations.

```cpp
struct TurnResult {
    std::vector<MoveInfo>        moves;                // Regular tile moves
    std::vector<MergeInfo>       merges;               // Regular merges
    std::set<pair<int,int>>      bomb_destroyed;       // Bomb-killed cells
    std::set<pair<int,int>>      snail_bomb_kills;     // Snails killed by bombs
    int                          points_gained;
    std::pair<int,int>           spawned_tile;         // (-1,-1) if none
    std::pair<int,int>           spawned_snail;
    bool                         board_changed;
    bool                         should_expand;
    std::string                  expand_direction;
    std::vector<PassiveCandidate>   passive_candidates;
    std::vector<SlowMoverUpdate>    slow_mover_updates;
    std::vector<RandomMoverUpdate>  random_mover_updates;
    std::vector<MoveInfo>           slow_tile_moves;
    std::vector<MergeInfo>          slow_tile_merges;
};
```

`points_gained` sums every merge channel: `merges`, `slow_tile_merges`, and `slow_mover_updates` entries with `is_merge` set.

---

## Python Bindings

**File**: `src/bindings.cpp`

pybind11 module `game2048_engine` exposes:

- `PassiveType` enum
- `MoveInfo`, `MergeInfo`, `PassiveCandidate`
- `SlowMoverState`, `SlowMoverUpdate`
- `RandomMoverState`, `RandomMoverUpdate`
- `TurnResult`
- `GameEngine` (all methods listed above)
- Free functions: `passive_name(PassiveType)`, `passive_description(PassiveType)`
