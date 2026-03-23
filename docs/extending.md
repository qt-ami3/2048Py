# Extending the Game

## Adding a New Passive

### 1. Define the flag in `passive.h`

```cpp
enum class PassiveType : int {
    NONE          = 0,
    A_LITTLE_SLOW = 1,
    CONTRARIAN    = 2,
    MY_PASSIVE    = 4,   // next power of two
};
```

### 2. Add name and description in `passive.cpp`

```cpp
std::string passive_name(PassiveType p) {
    switch (p) {
        case PassiveType::MY_PASSIVE: return "My Passive";
        // ...
    }
}

std::string passive_description(PassiveType p) {
    switch (p) {
        case PassiveType::MY_PASSIVE: return "Does something interesting.";
        // ...
    }
}
```

### 3. Implement the behavior class

Create `src/engine/include/my_behavior.h` and `src/engine/src/my_behavior.cpp`:

```cpp
// my_behavior.h
#pragma once
#include "tile_behavior.h"

class MyBehavior : public TileBehavior {
public:
    bool matches(PassiveType p) override;
    bool freeze_during_move() override;
    bool freeze_tile_behind() override;
    void pre_snapshot(Board&, ...) override;
    bool advance(MoveContext&, TurnResult&) override;
    bool blocks_cascade() override;
    bool requires_slow_mover_cleanup(PassiveType) override;
};
```

Implement the methods in `my_behavior.cpp`. Refer to `slow_behavior.cpp` or `contrarian_behavior.cpp` for patterns.

Key decisions:

| Method | Return `true` if… |
|--------|------------------|
| `freeze_during_move()` | This tile should be skipped during regular movement |
| `freeze_tile_behind()` | A same-value tile behind this one should also freeze |
| `blocks_cascade()` | Regular tiles should not slide past this tile when it vacates |
| `advance()` | Successfully moved at least one tile (return value is checked) |

### 4. Register in `GameEngine` constructor (`game_engine.cpp`)

```cpp
GameEngine::GameEngine(int rows, int cols) {
    behaviors_.push_back(std::make_unique<SlowBehavior>());
    behaviors_.push_back(std::make_unique<ContrarianBehavior>());
    behaviors_.push_back(std::make_unique<MyBehavior>());  // add here
    // ...
}
```

Registration order = advance order. The first behavior whose `matches()` returns `true` for a tile owns it.

### 5. Add to `CMakeLists.txt`

```cmake
pybind11_add_module(game2048_engine
    src/bindings.cpp
    # ... existing files ...
    src/my_behavior.cpp
)
```

### 6. (Optional) Expose to Python in `bindings.cpp`

If you need Python to check for the new passive type:

```cpp
py::enum_<PassiveType>(m, "PassiveType")
    // ... existing values ...
    .value("MY_PASSIVE", PassiveType::MY_PASSIVE);
```

### 7. Update the Python visual indicator

In `functions.py`, `draw_passive_indicator` checks bitmask bits. Add a new dot color for your passive:

```python
def draw_passive_indicator(g, r, c):
    pt = g.passive_map.get((r, c), 0)
    if pt & 4:  # MY_PASSIVE bit
        pygame.draw.circle(surface, YELLOW, (x + 30, indicator_y), 5)
    # ...
```

---

## Adding a New Ability

### 1. Add to `g.abilities` in `main.py`

```python
g.abilities = [
    {"name": "Bomb",   "cost": 750,  "charges": 0, "description": "..."},
    {"name": "Freeze", "cost": 500,  "charges": 0, "description": "..."},
    {"name": "Switch", "cost": 600,  "charges": 0, "description": "..."},
    {"name": "MyAbil", "cost": 400,  "charges": 0, "description": "Does X."},
]
```

### 2. Add a selection flag to `G()`

```python
g.selecting_myabil_position = False
```

### 3. Handle button click in `main.py`

In the mouse-click event handler, detect a click on the new button and set the flag:

```python
def handle_button_click(g, pos):
    # ... existing buttons ...
    if rect_myabil.collidepoint(pos) and g.abilities[3]["charges"] > 0:
        g.selecting_myabil_position = True
```

### 4. Handle tile click

When `g.selecting_myabil_position` is `True`, the next grid-tile click triggers your ability:

```python
def place_myabil_at_tile(g, r, c):
    g.abilities[3]["charges"] -= 1
    g.selecting_myabil_position = False
    # call engine method or mutate board directly
    g.engine.my_ability(r, c)
    sync_grid_from_engine(g)
```

### 5. Implement engine-side (if needed)

Add a method to `GameEngine`:

```cpp
// game_engine.h
void my_ability(int r, int c);

// game_engine.cpp
void GameEngine::my_ability(int r, int c) {
    // mutate board_
}
```

Expose via pybind11 in `bindings.cpp`:

```cpp
.def("my_ability", &GameEngine::my_ability)
```

### 6. Draw the new button

`draw_button` in `functions.py` handles rendering. The shop auto-scales to `len(g.abilities)` rows.

---

## Modifying Movement Rules

All segment-based movement is in `movement.cpp`. The four direction functions share a common segment-processing pattern:

1. Identify frozen tile positions to split the row/column into segments.
2. For each segment, call `process_segment_*()`.
3. Inside `process_segment`, handle merges, bomb detonations, and passive inheritance.

To change merge rules (e.g., allow 3-tile merges), modify the merge loop inside `process_segment_*`.

To change bomb behavior, modify the bomb check inside the segment processor.

---

## Changing Expansion Behavior

Board expansion is triggered when `g.engine.score() >= g.engine.tar_expand()`. The direction of expansion is chosen in `start_grid_expansion(g)` in `functions.py` (currently cycles or picks based on board state). To change the direction logic, edit that function.

`g.engine.complete_expansion(direction)` (C++) calls `board_.expand(direction)`, then updates all slow mover and snail positions to account for the shifted indices.
