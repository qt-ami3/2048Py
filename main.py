import pygame
import random as rand
import numpy as np
import functions as func

# pygame setup
pygame.init()

# Native monitor resolution (fullscreen)
NATIVE_WIDTH = 3840
NATIVE_HEIGHT = 2400

# Render resolution (lower for performance)
RENDER_WIDTH = 1920
RENDER_HEIGHT = 1200

# Windowed resolution (smaller for windowed mode)
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

# Fullscreen state
is_fullscreen = True

# Create display based on initial mode
if is_fullscreen:
    screen = pygame.display.set_mode((NATIVE_WIDTH, NATIVE_HEIGHT), pygame.FULLSCREEN)
    display_width, display_height = NATIVE_WIDTH, NATIVE_HEIGHT
else:
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    display_width, display_height = WINDOW_WIDTH, WINDOW_HEIGHT

# Create render surface at lower resolution
render_surface = pygame.Surface((RENDER_WIDTH, RENDER_HEIGHT))

# Use render surface dimensions for game logic
screen_width = RENDER_WIDTH
screen_height = RENDER_HEIGHT

clock = pygame.time.Clock()
running = True

pygame.font.init()
font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 29)
small_font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 20)
#font = pygame.font.Font("fonts/mapleMono.ttf", 29)
#small_font = pygame.font.Font("fonts/mapleMono.ttf", 20)

# Grid config
square_size = 100
rows, cols = 4, 4

grid_width = cols * square_size
grid_height = rows * square_size

start_x = (RENDER_WIDTH - grid_width) // 2
start_y = (RENDER_HEIGHT - grid_height) // 2

playingGrid = np.zeros((rows, cols), dtype=int)

playingGrid[rand.randint(0,3)][rand.randint(0,3)] = 2
playingGrid[rand.randint(0,3)][rand.randint(0,3)] = 2

playingGridLast = playingGrid.copy()

# Score tracking - start with initial tiles
# points = sum(sum(playingGrid))
points = 750

# Ability system
bomb_ability_cost = 750
bomb_ability_active = False
next_tile_is_bomb = False
selecting_bomb_position = False  # True when player needs to select where to place bomb
hovered_tile = None  # (r, c) of tile being hovered over
bomb_image = None
try:
    bomb_image = pygame.image.load("assets/sprites/bomb.png")
    bomb_image = pygame.transform.scale(bomb_image, (80, 80))
except:
    print("Warning: Could not load bomb.png")

# Menu configuration
menu_height = 150
menu_y = start_y + grid_height + 30
button_width = 200
button_height = 60
button_x = start_x + (grid_width - button_width) // 2

# Animation variables
animating = False
animation_progress = 0
animation_speed = 0.15  # Controls animation speed (0-1, higher = faster)
moving_tiles = []  # List of (start_r, start_c, end_r, end_c, value, progress)
merging_tiles = []  # List of (r, c, value, scale)
new_tile_pos = None  # Position of newly spawned tile
new_tile_scale = 0  # Scale for new tile animation

# Grid expansion animation
grid_expanding = False
expand_progress = 0
expand_speed = 0.03
pending_expand = False
expand_old_rows = 0
expand_old_cols = 0
expand_old_sx = 0
expand_old_sy = 0

# Color scheme
COLORS = {
    0: "#4c566a",
    2: "#88c0d0",
    4: "#81a1c1",
    8: "#5e81ac",
    16: "#bf616a",
    32: "#d08770",
    64: "#ebcb8b",
    128: "#a3be8c",
    256: "#b48ead",
    512: "#8fbcbb",
    1024: "#5e81ac",
    2048: "#bf616a",
    -1: "#bf616a",  # Bomb tile color
}

# CRT effect variables
crt_surface = pygame.Surface((screen_width, screen_height))
scanline_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
vignette_surface = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)

# Create scanlines
for y in range(0, screen_height, 3):
    pygame.draw.line(scanline_surface, (0, 0, 0, 40), (0, y), (screen_width, y), 1)

# Create vignette effect
for i in range(255):
    alpha = int((i / 255) ** 2 * 120)
    distance_x = int(i * screen_width / 255 / 2)
    distance_y = int(i * screen_height / 255 / 2)
    pygame.draw.rect(vignette_surface, (0, 0, 0, alpha), 
                     (distance_x, distance_y, screen_width - distance_x * 2, screen_height - distance_y * 2), 1)

def get_tile_color(value):
    return COLORS.get(value, "#2e3440")

def lerp(start, end, t):
    """Linear interpolation"""
    return start + (end - start) * t

def ease_out_cubic(t):
    """Easing function for smooth animation"""
    return 1 - pow(1 - t, 3)

# Pre-rendered tile surface cache
tile_cache = {}

def init_tile_cache():
    for value in list(COLORS.keys()):
        if value == 0:
            continue
        surface = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
        color = pygame.Color(get_tile_color(value))
        pygame.draw.rect(surface, color, (0, 0, square_size, square_size))
        pygame.draw.rect(surface, "#d8dee9", (0, 0, square_size, square_size), 2)
        if value == -1 and bomb_image:
            bomb_scaled = pygame.transform.scale(bomb_image, (int(square_size * 0.8), int(square_size * 0.8)))
            bomb_rect = bomb_scaled.get_rect(center=(square_size // 2, square_size // 2))
            surface.blit(bomb_scaled, bomb_rect)
        else:
            text = font.render(str(value), True, "#eceff4")
            text_rect = text.get_rect(center=(square_size // 2, square_size // 2))
            surface.blit(text, text_rect)
        tile_cache[value] = surface

init_tile_cache()

# Score text cache
_score_cache = {'text': None, 'surface': None}

def get_cached_score(score_value):
    text = f"Score: {score_value}"
    if _score_cache['text'] != text:
        _score_cache['text'] = text
        _score_cache['surface'] = font.render(text, True, "#eceff4")
    return _score_cache['surface']

def prepare_tile_surface(value, scale):
    """Create a scaled tile surface - safe for thread pool execution"""
    if scale == 1.0 and value in tile_cache:
        return tile_cache[value]
    scaled_size = max(int(square_size * scale), 1)
    if value in tile_cache:
        return pygame.transform.smoothscale(tile_cache[value], (scaled_size, scaled_size))
    surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
    color = pygame.Color(get_tile_color(value))
    pygame.draw.rect(surface, color, (0, 0, scaled_size, scaled_size))
    pygame.draw.rect(surface, "#d8dee9", (0, 0, scaled_size, scaled_size), 2)
    if value == -1 and bomb_image:
        bsz = int(scaled_size * 0.8)
        bomb_s = pygame.transform.scale(bomb_image, (bsz, bsz))
        bomb_r = bomb_s.get_rect(center=(scaled_size // 2, scaled_size // 2))
        surface.blit(bomb_s, bomb_r)
    elif value != 0:
        text = font.render(str(value), True, "#eceff4")
        text_r = text.get_rect(center=(scaled_size // 2, scaled_size // 2))
        surface.blit(text, text_r)
    return surface

def toggle_fullscreen():
    """Toggle between fullscreen and windowed mode"""
    global is_fullscreen, screen, display_width, display_height
    
    is_fullscreen = not is_fullscreen
    
    if is_fullscreen:
        screen = pygame.display.set_mode((NATIVE_WIDTH, NATIVE_HEIGHT), pygame.FULLSCREEN)
        display_width, display_height = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        display_width, display_height = WINDOW_WIDTH, WINDOW_HEIGHT

def start_grid_expansion():
    global rows, cols, playingGrid, playingGridLast, grid_width, grid_height
    global start_x, start_y, menu_y, button_x
    global grid_expanding, expand_progress, expand_old_rows, expand_old_cols
    global expand_old_sx, expand_old_sy

    expand_old_sx = start_x
    expand_old_sy = start_y
    expand_old_rows = rows
    expand_old_cols = cols

    if rand.choice([True, False]):
        rows += 1
    else:
        cols += 1

    new_grid = np.zeros((rows, cols), dtype=int)
    new_grid[:expand_old_rows, :expand_old_cols] = playingGrid
    playingGrid = new_grid
    playingGridLast = playingGrid.copy()

    grid_width = cols * square_size
    grid_height = rows * square_size
    start_x = (RENDER_WIDTH - grid_width) // 2
    start_y = (RENDER_HEIGHT - grid_height) // 2
    menu_y = start_y + grid_height + 30
    button_x = start_x + (grid_width - button_width) // 2

    grid_expanding = True
    expand_progress = 0

    print(f"Grid expanded to {rows}x{cols}!")

def process_move(direction):
    global playingGrid, playingGridLast, animating, moving_tiles, merging_tiles
    global animation_progress, new_tile_pos, new_tile_scale, points, next_tile_is_bomb, pending_expand
    
    if animating:
        return
    
    # Store grid before move
    grid_before = playingGrid.copy()
    
    # Execute move and get animation data
    if direction == "up":
        moves, merges = func.moveUp(playingGrid, rows, cols)
    elif direction == "down":
        moves, merges = func.moveDown(playingGrid, rows, cols)
    elif direction == "left":
        moves, merges = func.moveLeft(playingGrid, rows, cols)
    elif direction == "right":
        moves, merges = func.moveRight(playingGrid, rows, cols)
    
    # Check if grid actually changed
    if np.array_equal(grid_before, playingGrid):
        return
    
    # Calculate points from merges (each merge adds the value of the new tile created)
    points_gained = sum(value for _, _, value in merges)
    
    # Setup animations
    if moves or merges:
        animating = True
        animation_progress = 0
        moving_tiles = [(sr, sc, er, ec, val, 0) for sr, sc, er, ec, val in moves]
        merging_tiles = [(r, c, val, 1.0) for r, c, val in merges]
        
        # Add new tile (regular only - bombs are placed manually)
        new_pos = func.newNum(playingGrid)
        
        if new_pos:
            new_tile_pos = new_pos
            new_tile_scale = 0
            r, c = new_pos
            if playingGrid[r][c] > 0:  # Only add points for regular tiles
                points_gained += playingGrid[r][c]
        
        points += points_gained

        # Check if any merge created a 2048 tile
        if any(val == 2048 for _, _, val in merges):
            pending_expand = True

        playingGridLast = playingGrid.copy()
        print()
        print(f"Score: {points} (+{points_gained})")

def update_animations(dt):
    global animating, animation_progress, moving_tiles, merging_tiles, new_tile_scale, new_tile_pos
    global grid_expanding, expand_progress, pending_expand

    # Update grid expansion animation
    if grid_expanding:
        expand_progress += expand_speed
        if expand_progress >= 1.0:
            grid_expanding = False
            expand_progress = 0
        return

    if not animating:
        return
    
    # Update animation progress
    animation_progress += animation_speed
    
    # Update moving tiles
    eased_progress = ease_out_cubic(min(animation_progress, 1.0))
    moving_tiles = [(sr, sc, er, ec, val, eased_progress) for sr, sc, er, ec, val, _ in moving_tiles]
    
    # Update merging tiles (scale effect)
    if animation_progress > 0.6:
        merge_progress = (animation_progress - 0.6) / 0.4
        for i, (r, c, val, _) in enumerate(merging_tiles):
            if merge_progress < 0.5:
                scale = 1.0 + merge_progress * 0.4  # Scale up to 1.2
            else:
                scale = 1.2 - (merge_progress - 0.5) * 0.4  # Scale back to 1.0
            merging_tiles[i] = (r, c, val, scale)
    
    # Update new tile animation
    if new_tile_pos and animation_progress > 0.7:
        new_tile_scale = min((animation_progress - 0.7) / 0.3, 1.0)
    
    # End animation
    if animation_progress >= 1.0:
        animating = False
        moving_tiles = []
        merging_tiles = []
        new_tile_pos = None
        new_tile_scale = 0
        if pending_expand:
            pending_expand = False
            start_grid_expansion()

def draw_tile(r, c, value, scale=1.0, alpha=255):
    x = start_x + c * square_size
    y = start_y + r * square_size

    # Fast path: blit directly from cache for standard tiles
    if scale == 1.0 and alpha == 255 and value in tile_cache:
        render_surface.blit(tile_cache[value], (x, y))
        return

    scaled_size = max(int(square_size * scale), 1)
    offset = (square_size - scaled_size) / 2

    if value in tile_cache:
        tile_surface = pygame.transform.smoothscale(tile_cache[value], (scaled_size, scaled_size))
    else:
        tile_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
        color = pygame.Color(get_tile_color(value))
        color.a = alpha
        pygame.draw.rect(tile_surface, color, (0, 0, scaled_size, scaled_size))
        pygame.draw.rect(tile_surface, "#d8dee9", (0, 0, scaled_size, scaled_size), 2)
        if value == -1 and bomb_image:
            bomb_scaled = pygame.transform.scale(bomb_image, (int(scaled_size * 0.8), int(scaled_size * 0.8)))
            bomb_rect = bomb_scaled.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(bomb_scaled, bomb_rect)
        elif value != 0:
            text = font.render(str(value), True, "#eceff4")
            text_rect = text.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(text, text_rect)

    if alpha != 255:
        tile_surface.set_alpha(alpha)

    render_surface.blit(tile_surface, (x + offset, y + offset))

def draw_button(x, y, width, height, text, cost, can_afford, active=False):
    """Draw ability button"""
    # Button background
    if can_afford and not active:
        color = "#81a1c1"
        hover_color = "#5e81ac"
    elif active:
        color = "#a3be8c"
        hover_color = "#a3be8c"
    else:
        color = "#4c566a"
        hover_color = "#4c566a"
    
    # Check hover
    mouse_pos = pygame.mouse.get_pos()
    # Scale mouse position to render coordinates
    mouse_x = mouse_pos[0] * RENDER_WIDTH / display_width
    mouse_y = mouse_pos[1] * RENDER_HEIGHT / display_height
    
    is_hover = x <= mouse_x <= x + width and y <= mouse_y <= y + height
    
    button_color = hover_color if is_hover else color
    
    # Draw button
    pygame.draw.rect(render_surface, button_color, (x, y, width, height))
    pygame.draw.rect(render_surface, "#d8dee9", (x, y, width, height), 3)
    
    # Draw text
    if active:
        button_text = small_font.render("ACTIVE", True, "#eceff4")
    else:
        button_text = small_font.render(text, True, "#eceff4")
    text_rect = button_text.get_rect(center=(x + width//2, y + height//3))
    render_surface.blit(button_text, text_rect)
    
    # Draw cost
    if not active:
        cost_color = "#a3be8c" if can_afford else "#bf616a"
        cost_text = small_font.render(f"Cost: {cost}", True, cost_color)
        cost_rect = cost_text.get_rect(center=(x + width//2, y + 2*height//3))
        render_surface.blit(cost_text, cost_rect)
    
    return is_hover and can_afford and not active

def handle_button_click(mouse_pos):
    """Handle button clicks"""
    global points, next_tile_is_bomb, selecting_bomb_position
    
    # Scale mouse position to render coordinates
    mouse_x = mouse_pos[0] * RENDER_WIDTH / display_width
    mouse_y = mouse_pos[1] * RENDER_HEIGHT / display_height
    
    # Check bomb button (use the actual button Y position)
    button_y = menu_y + 30
    if button_x <= mouse_x <= button_x + button_width and button_y <= mouse_y <= button_y + button_height:
        if points >= bomb_ability_cost and not selecting_bomb_position:
            points -= bomb_ability_cost
            selecting_bomb_position = True
            print(f"Bomb ability activated! Click an empty tile to place the bomb. Score: {points}")

def get_tile_from_mouse(mouse_pos):
    """Convert mouse position to grid coordinates"""
    mouse_x = mouse_pos[0] * RENDER_WIDTH / display_width
    mouse_y = mouse_pos[1] * RENDER_HEIGHT / display_height
    
    # Check if mouse is within grid bounds
    if start_x <= mouse_x <= start_x + grid_width and start_y <= mouse_y <= start_y + grid_height:
        c = int((mouse_x - start_x) // square_size)
        r = int((mouse_y - start_y) // square_size)
        
        # Ensure within bounds
        if 0 <= r < rows and 0 <= c < cols:
            return (r, c)
    
    return None

def place_bomb_at_tile(r, c):
    """Place a bomb at the specified tile with animation"""
    global playingGrid, selecting_bomb_position, animating, new_tile_pos, new_tile_scale, animation_progress
    
    if playingGrid[r][c] == 0:  # Only place on empty tiles
        playingGrid[r][c] = -1
        selecting_bomb_position = False
        
        # Trigger spawn animation
        animating = True
        animation_progress = 0.7  # Start at the new tile animation phase
        new_tile_pos = (r, c)
        new_tile_scale = 0
        
        print(f"Bomb placed at position ({r}, {c})")

while running: # game logic game loop
    dt = clock.tick(60) / 1000.0  # Delta time in seconds

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and not animating and not grid_expanding:
            match event.key:
                case pygame.K_UP: 
                    process_move("up")
                case pygame.K_DOWN:
                    process_move("down")
                case pygame.K_LEFT:
                    process_move("left")
                case pygame.K_RIGHT:
                    process_move("right")
                case pygame.K_ESCAPE:
                    if selecting_bomb_position:
                        # Cancel bomb selection
                        selecting_bomb_position = False
                        points += bomb_ability_cost  # Refund
                        print("Bomb placement cancelled. Points refunded.")
                    else:
                        running = False
                case pygame.K_F11:
                    toggle_fullscreen()
        
        if event.type == pygame.MOUSEMOTION:
            if selecting_bomb_position:
                hovered_tile = get_tile_from_mouse(event.pos)
        
        if event.type == pygame.MOUSEBUTTONDOWN and not animating and not grid_expanding:
            if event.button == 1:  # Left click
                if selecting_bomb_position:
                    # Try to place bomb on clicked tile
                    tile = get_tile_from_mouse(event.pos)
                    if tile:
                        r, c = tile
                        place_bomb_at_tile(r, c)
                else:
                    # Normal button click
                    handle_button_click(event.pos)

    # Update animations
    update_animations(dt)

    # Draw background on render surface
    render_surface.fill("#4c566a")
    
    # Draw score (cached - only re-renders when score changes)
    score_text = get_cached_score(points)
    render_surface.blit(score_text, (50, 50))

    # Temporarily override start positions for expansion animation
    _expand_real_sx, _expand_real_sy = start_x, start_y
    if grid_expanding:
        t = ease_out_cubic(expand_progress)
        start_x = int(lerp(expand_old_sx, _expand_real_sx, t))
        start_y = int(lerp(expand_old_sy, _expand_real_sy, t))

    # Draw grid cells
    for r in range(rows):
        for c in range(cols):
            x = start_x + c * square_size
            y = start_y + r * square_size

            is_new_cell = grid_expanding and (r >= expand_old_rows or c >= expand_old_cols)

            # Highlight hovered empty tile during bomb selection
            if selecting_bomb_position and hovered_tile == (r, c) and playingGrid[r][c] == 0:
                pygame.draw.rect(render_surface, "#a3be8c", (x, y, square_size, square_size))
                pygame.draw.rect(render_surface, "#d8dee9", (x, y, square_size, square_size), 4)
            elif is_new_cell:
                # New cell stretches/fades in during expansion
                alpha = int(255 * ease_out_cubic(expand_progress))
                cell_scale = ease_out_cubic(expand_progress)
                scaled = max(int(square_size * cell_scale), 1)
                off = (square_size - scaled) // 2
                cell_surf = pygame.Surface((scaled, scaled), pygame.SRCALPHA)
                border_color = pygame.Color("#d8dee9")
                pygame.draw.rect(cell_surf, (border_color.r, border_color.g, border_color.b, alpha),
                               (0, 0, scaled, scaled), 2)
                render_surface.blit(cell_surf, (x + off, y + off))
            else:
                pygame.draw.rect(render_surface, "#d8dee9", (x, y, square_size, square_size), 2)

    # Draw tiles
    if not animating:
        # Static tiles: blit directly from cache (no threading needed)
        for r in range(rows):
            for c in range(cols):
                value = playingGrid[r][c]
                if value:
                    draw_tile(r, c, value)
    else:
        merging_positions = {(r, c) for r, c, _, _ in merging_tiles}

        # Draw static tiles from cache
        for r in range(rows):
            for c in range(cols):
                value = playingGrid[r][c]
                if value and (r, c) not in merging_positions and (r, c) != new_tile_pos:
                    is_moving_destination = any(er == r and ec == c for _, _, er, ec, _, _ in moving_tiles)
                    if not is_moving_destination or animation_progress >= 1.0:
                        draw_tile(r, c, value)

        # Draw moving tiles from cache
        for sr, sc, er, ec, val, progress in moving_tiles:
            r_pos = lerp(sr, er, progress)
            c_pos = lerp(sc, ec, progress)
            draw_tile(r_pos, c_pos, val)

        # Draw merging tiles
        for mr, mc, mval, mscale in merging_tiles:
            if mscale == 1.0:
                draw_tile(mr, mc, mval)
            else:
                surface = prepare_tile_surface(mval, mscale)
                if surface:
                    x = start_x + mc * square_size
                    y = start_y + mr * square_size
                    offset = (square_size - surface.get_width()) / 2
                    render_surface.blit(surface, (x + offset, y + offset))

        # Draw new tile spawn animation
        if new_tile_pos and new_tile_scale > 0:
            nr, nc = new_tile_pos
            nscale = ease_out_cubic(new_tile_scale)
            surface = prepare_tile_surface(playingGrid[nr][nc], nscale)
            if surface:
                x = start_x + nc * square_size
                y = start_y + nr * square_size
                offset = (square_size - surface.get_width()) / 2
                render_surface.blit(surface, (x + offset, y + offset))

    # Restore start positions after expansion animation drawing
    if grid_expanding:
        start_x, start_y = _expand_real_sx, _expand_real_sy

    # Draw ability menu
    if selecting_bomb_position:
        instruction_text = small_font.render("Click an empty tile to place bomb (ESC to cancel)", True, "#a3be8c")
        instruction_rect = instruction_text.get_rect(center=(RENDER_WIDTH//2, menu_y)) # x, y position
        render_surface.blit(instruction_text, instruction_rect)
    else:
        menu_title = font.render("ABILITIES", True, "#eceff4")
        menu_title_rect = menu_title.get_rect(center=(RENDER_WIDTH//2, menu_y))
        render_surface.blit(menu_title, menu_title_rect)
    
    # Draw bomb button
    can_afford = points >= bomb_ability_cost
    draw_button(button_x, menu_y + 30, button_width, button_height, 
                "Bomb Tile", bomb_ability_cost, can_afford, selecting_bomb_position)
    
    # Apply CRT effects on render surface
    crt_surface.blit(render_surface, (0, 0))
    
    # 2. Add slight glow/bloom effect
    glow_surface = crt_surface.copy()
    glow_surface.set_alpha(30)
    render_surface.blit(glow_surface, (2, 2))
    render_surface.blit(glow_surface, (-2, -2))
    
    # 3. Apply scanlines
    render_surface.blit(scanline_surface, (0, 0))
    
    # 4. Apply vignette
    render_surface.blit(vignette_surface, (0, 0))
    
    # 5. Add slight RGB shift for chromatic aberration
    if animating:  # Add subtle shift during animations
        shift_amount = int(abs(np.sin(animation_progress * np.pi)) * 2)
        if shift_amount > 0:
            # Red channel shift
            red_surface = render_surface.copy()
            red_surface.set_alpha(100)
            render_surface.blit(red_surface, (shift_amount, 0))
    
    # Scale up the render surface to current display resolution and show
    pygame.transform.scale(render_surface, (display_width, display_height), screen)
    pygame.display.flip()


pygame.quit()
