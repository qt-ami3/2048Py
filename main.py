#   shaders from libretro/gist-shaders
#   never declare functions in main

import pygame
import numpy as np
import functions as func
import moderngl

# pygame setup
pygame.init()

# Game state container
class G: pass
g = G()

# Native monitor resolution (fullscreen) / display resolution
g.NATIVE_WIDTH = 1920
g.NATIVE_HEIGHT = 1200

# Render resolution (lower for performance)
g.RENDER_WIDTH = 3840
g.RENDER_HEIGHT = 2400

# Windowed resolution (smaller for windowed mode)
g.WINDOW_WIDTH = 1280
g.WINDOW_HEIGHT = 800

# Fullscreen state
g.is_fullscreen = True

# Create display based on initial mode with OpenGL support
if g.is_fullscreen:
    g.screen = pygame.display.set_mode((g.NATIVE_WIDTH, g.NATIVE_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN)
    g.display_width, g.display_height = g.NATIVE_WIDTH, g.NATIVE_HEIGHT
else:
    g.screen = pygame.display.set_mode((g.WINDOW_WIDTH, g.WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
    g.display_width, g.display_height = g.WINDOW_WIDTH, g.WINDOW_HEIGHT

# Initialize ModernGL
g.ctx = moderngl.create_context()

# Create render surface at lower resolution
g.render_surface = pygame.Surface((g.RENDER_WIDTH, g.RENDER_HEIGHT))

clock = pygame.time.Clock()
running = True

pygame.font.init()
g.font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 29)
g.small_font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 20)

# UI Configuration - centralized sizing and spacing
g.ui_config = {
    # Grid settings
    'square_size': 150,        # Width and height of each grid tile in pixels
    'initial_rows': 4,         # Number of rows when game starts
    'initial_cols': 4,         # Number of columns when game starts

    # Menu settings
    'menu_height': 150,        # Total height reserved for menu area below grid
    'menu_spacing': 90,        # Vertical gap between bottom of grid and top of menu
    'button_width': 200,       # Width of ability buttons (e.g., Bomb Tile button)
    'button_height': 60,       # Height of ability buttons

    # Visual settings
    'grid_border_width': 2,    # Thickness of borders around empty grid cells
    'tile_border_width': 2,    # Thickness of borders around number tiles
    'bomb_scale': 0.8,         # Bomb sprite size as a ratio of tile size (0.8 = 80% of tile)

    # Spacing
    'score_x': 50,             # X position of score text from left edge
    'score_y': 50,             # Y position of score text from top edge
}

# Grid state - tracks current grid dimensions and tile size
g.rows, g.cols = g.ui_config['initial_rows'], g.ui_config['initial_cols']
g.square_size = g.ui_config['square_size']

# Calculated positions
g.grid_width = 0
g.grid_height = 0
g.start_x = 0
g.start_y = 0
g.menu_y = 0
g.button_x = 0
g.tarExpand = 2048
g.button_width = g.ui_config['button_width']
g.button_height = g.ui_config['button_height']
g.menu_height = g.ui_config['menu_height']

# Initialize positions
func.recalculate_positions(g)

# Initialize playing grid
g.playingGrid = np.zeros((g.rows, g.cols), dtype=int)

func.newNum(g.playingGrid)
func.newNum(g.playingGrid)

g.playingGridLast = g.playingGrid.copy()

# Score tracking - start with initial tiles
g.points = 4500

# Ability system
g.abilities = [
    {'name': 'Bomb', 'cost': 750, 'charges': 0, 'description': 'Destroy a tile'},
    {'name': 'Freeze', 'cost': 500, 'charges': 0, 'description': 'Hold tile 1 turn'},
]
g.selecting_bomb_position = False
g.selecting_freeze_position = False
g.frozen_tiles = set()
g.hovered_tile = None
g.bomb_image = None
# Shop state
g.shop_open = True  # Start with shop open
g.pending_shop = False
try:
    g.bomb_image = pygame.image.load("assets/sprites/bomb.png")
    bomb_size = int(g.square_size * g.ui_config['bomb_scale'])
    g.bomb_image = pygame.transform.scale(g.bomb_image, (bomb_size, bomb_size))
except:
    print("Warning: Could not load bomb.png")

# Animation variables
g.animating = False
g.animation_progress = 0
g.animation_speed = 0.15
g.moving_tiles = []
g.merging_tiles = []
g.new_tile_pos = None
g.new_tile_scale = 0

# Grid expansion animation
g.grid_expanding = False
g.expand_progress = 0
g.expand_speed = 0.03
g.pending_expand = False
g.expand_old_rows = 0
g.expand_old_cols = 0
g.expand_old_sx = 0
g.expand_old_sy = 0
g.expand_direction = ""

# Pre-rendered tile surface cache
g.tile_cache = {}
g._score_cache = {'text': None, 'surface': None}
func.init_tile_cache(g)

# CRT Shader parameters
g.crt_params = {
    'hardScan': -10.0,
    'hardPix': 0.7,
    'warpX': 0.12,
    'warpY': 0.14,
    'maskDark': 0.3,
    'maskLight': 1.8,
    'shadowMask': 0.0,
    'brightBoost': 1.1,
    'hardBloomPix': -1.5,
    'hardBloomScan': -2.0,
    'bloomAmount': 0.20,
    'shape': 2.0
}

# Setup ModernGL shader
g.prog = g.ctx.program(vertex_shader=func.vertex_shader, fragment_shader=func.fragment_shader)

# Create fullscreen quad
vertices = np.array([
    -1.0, -1.0,  0.0, 0.0,
    1.0, -1.0,  1.0, 0.0,
    -1.0,  1.0,  0.0, 1.0,
    1.0,  1.0,  1.0, 1.0,
], dtype='f4')

vbo = g.ctx.buffer(vertices.tobytes())
g.vao = g.ctx.simple_vertex_array(g.prog, vbo, 'in_vert', 'in_texcoord')

# Create texture for pygame surface
g.texture = g.ctx.texture((g.RENDER_WIDTH, g.RENDER_HEIGHT), 3)
g.texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
g.texture.repeat_x = False
g.texture.repeat_y = False

# Setup framebuffer for rendering
g.fbo = g.ctx.framebuffer(color_attachments=[g.ctx.texture((g.display_width, g.display_height), 4)])

while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Shop intercepts all input when open
        if g.shop_open:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                func.handle_shop_click(g, event.pos)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    g.shop_open = False
                elif event.key == pygame.K_F11:
                    func.toggle_fullscreen(g)
            continue

        if event.type == pygame.KEYDOWN and not g.animating and not g.grid_expanding:
            match event.key:
                case pygame.K_UP:
                    func.process_move(g, "up")
                case pygame.K_DOWN:
                    func.process_move(g, "down")
                case pygame.K_LEFT:
                    func.process_move(g, "left")
                case pygame.K_RIGHT:
                    func.process_move(g, "right")
                case pygame.K_ESCAPE:
                    if g.selecting_bomb_position:
                        g.selecting_bomb_position = False
                        g.abilities[0]['charges'] += 1
                        print("Bomb placement cancelled. Charge refunded.")
                    elif g.selecting_freeze_position:
                        g.selecting_freeze_position = False
                        g.abilities[1]['charges'] += 1
                        print("Freeze cancelled. Charge refunded.")
                    else:
                        running = False
                case pygame.K_F11:
                    func.toggle_fullscreen(g)

        if event.type == pygame.MOUSEMOTION:
            if g.selecting_bomb_position or g.selecting_freeze_position:
                g.hovered_tile = func.get_tile_from_mouse(g, event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and not g.animating and not g.grid_expanding:
            if event.button == 1:
                if g.selecting_bomb_position:
                    tile = func.get_tile_from_mouse(g, event.pos)
                    if tile:
                        r, c = tile
                        func.place_bomb_at_tile(g, r, c)
                elif g.selecting_freeze_position:
                    tile = func.get_tile_from_mouse(g, event.pos)
                    if tile:
                        r, c = tile
                        func.place_freeze_on_tile(g, r, c)
                else:
                    func.handle_button_click(g, event.pos)

    func.update_animations(g, dt)

    # Draw to pygame surface
    g.render_surface.fill("#4c566a")

    # Draw score (cached - only re-renders when score changes)
    score_text = func.get_cached_score(g, g.points)
    g.render_surface.blit(score_text, (g.ui_config['score_x'], g.ui_config['score_y']))

    # Temporarily override start positions for expansion animation
    _expand_real_sx, _expand_real_sy = g.start_x, g.start_y
    if g.grid_expanding:
        t = func.ease_out_cubic(g.expand_progress)
        g.start_x = int(func.lerp(g.expand_old_sx, _expand_real_sx, t))
        g.start_y = int(func.lerp(g.expand_old_sy, _expand_real_sy, t))

    for r in range(g.rows):
        for c in range(g.cols):
            x = g.start_x + c * g.square_size
            y = g.start_y + r * g.square_size

            if g.grid_expanding:
                if g.expand_direction == "down":
                    is_new_cell = r >= g.expand_old_rows
                elif g.expand_direction == "up":
                    is_new_cell = r == 0
                elif g.expand_direction == "right":
                    is_new_cell = c >= g.expand_old_cols
                elif g.expand_direction == "left":
                    is_new_cell = c == 0
                else:
                    is_new_cell = False
            else:
                is_new_cell = False

            if g.selecting_bomb_position and g.hovered_tile == (r, c) and g.playingGrid[r][c] == 0:
                pygame.draw.rect(g.render_surface, "#a3be8c", (x, y, g.square_size, g.square_size))
                pygame.draw.rect(g.render_surface, "#d8dee9", (x, y, g.square_size, g.square_size), 4)
            elif g.selecting_freeze_position and g.hovered_tile == (r, c) and g.playingGrid[r][c] > 0 and (r, c) not in g.frozen_tiles:
                pygame.draw.rect(g.render_surface, "#88c0d0", (x, y, g.square_size, g.square_size))
                pygame.draw.rect(g.render_surface, "#d8dee9", (x, y, g.square_size, g.square_size), 4)
            elif is_new_cell:
                # New cell stretches/fades in during expansion
                alpha = int(255 * func.ease_out_cubic(g.expand_progress))
                cell_scale = func.ease_out_cubic(g.expand_progress)
                scaled = max(int(g.square_size * cell_scale), 1)
                off = (g.square_size - scaled) // 2
                cell_surf = pygame.Surface((scaled, scaled), pygame.SRCALPHA)
                border_color = pygame.Color("#d8dee9")
                pygame.draw.rect(cell_surf, (border_color.r, border_color.g, border_color.b, alpha),
                               (0, 0, scaled, scaled), g.ui_config['grid_border_width'])
                g.render_surface.blit(cell_surf, (x + off, y + off))
            else:
                pygame.draw.rect(g.render_surface, "#d8dee9", (x, y, g.square_size, g.square_size), g.ui_config['grid_border_width'])

    # Draw tiles
    if not g.animating:
        # Static tiles: blit directly from cache (no threading needed)
        for r in range(g.rows):
            for c in range(g.cols):
                value = g.playingGrid[r][c]
                if value:
                    func.draw_tile(g, r, c, value)
    else:
        merging_positions = {(r, c) for r, c, _, _ in g.merging_tiles}

        # Draw static tiles from cache
        for r in range(g.rows):
            for c in range(g.cols):
                value = g.playingGrid[r][c]
                if value and (r, c) not in merging_positions and (r, c) != g.new_tile_pos:
                    is_moving_destination = any(er == r and ec == c for _, _, er, ec, _, _ in g.moving_tiles)
                    if not is_moving_destination or g.animation_progress >= 1.0:
                        func.draw_tile(g, r, c, value)

        # Draw moving tiles from cache
        for sr, sc, er, ec, val, progress in g.moving_tiles:
            r_pos = func.lerp(sr, er, progress)
            c_pos = func.lerp(sc, ec, progress)
            func.draw_tile(g, r_pos, c_pos, val)

        # Draw merging tiles
        for mr, mc, mval, mscale in g.merging_tiles:
            if mscale == 1.0:
                func.draw_tile(g, mr, mc, mval)
            else:
                surface = func.prepare_tile_surface(g, mval, mscale)
                if surface:
                    x = g.start_x + mc * g.square_size
                    y = g.start_y + mr * g.square_size
                    offset = (g.square_size - surface.get_width()) / 2
                    g.render_surface.blit(surface, (x + offset, y + offset))

        # Draw new tile spawn animation
        if g.new_tile_pos and g.new_tile_scale > 0:
            nr, nc = g.new_tile_pos
            nscale = func.ease_out_cubic(g.new_tile_scale)
            surface = func.prepare_tile_surface(g, g.playingGrid[nr][nc], nscale)
            if surface:
                x = g.start_x + nc * g.square_size
                y = g.start_y + nr * g.square_size
                offset = (g.square_size - surface.get_width()) / 2
                g.render_surface.blit(surface, (x + offset, y + offset))

    # Draw frozen tile overlay (blue tint)
    for (fr, fc) in g.frozen_tiles:
        if 0 <= fr < g.rows and 0 <= fc < g.cols and g.playingGrid[fr][fc] != 0:
            fx = g.start_x + fc * g.square_size
            fy = g.start_y + fr * g.square_size
            tint = pygame.Surface((g.square_size, g.square_size), pygame.SRCALPHA)
            tint.fill((100, 160, 220, 80))
            g.render_surface.blit(tint, (fx, fy))

    # Restore start positions after expansion animation drawing
    if g.grid_expanding:
        g.start_x, g.start_y = _expand_real_sx, _expand_real_sy

    if g.selecting_bomb_position:
        instruction_text = g.small_font.render("Click an empty tile to place bomb (ESC to cancel)", True, "#a3be8c")
        instruction_rect = instruction_text.get_rect(center=(g.RENDER_WIDTH//2, g.menu_y - 30))
        g.render_surface.blit(instruction_text, instruction_rect)
    elif g.selecting_freeze_position:
        instruction_text = g.small_font.render("Click a number tile to freeze it (ESC to cancel)", True, "#88c0d0")
        instruction_rect = instruction_text.get_rect(center=(g.RENDER_WIDTH//2, g.menu_y - 30))
        g.render_surface.blit(instruction_text, instruction_rect)
    else:
        menu_title = g.font.render("ABILITIES", True, "#eceff4")
        menu_title_rect = menu_title.get_rect(center=(g.RENDER_WIDTH//2, g.menu_y))
        g.render_surface.blit(menu_title, menu_title_rect)

    # Draw two ability buttons side by side
    button_gap = 20
    total_w = g.button_width * 2 + button_gap
    btn_left_x = g.start_x + (g.grid_width - total_w) // 2
    btn_right_x = btn_left_x + g.button_width + button_gap
    btn_y = g.menu_y + 30

    bomb = g.abilities[0]
    func.draw_button(g, btn_left_x, btn_y, g.button_width, g.button_height,
                "Bomb Tile", bomb['charges'], bomb['charges'] > 0, g.selecting_bomb_position)

    freeze = g.abilities[1]
    func.draw_button(g, btn_right_x, btn_y, g.button_width, g.button_height,
                "Freeze", freeze['charges'], freeze['charges'] > 0, g.selecting_freeze_position)

    # Draw shop overlay on top of everything
    if g.shop_open:
        func.draw_shop(g)

    # Render to OpenGL with CRT shader
    func.render_to_opengl(g)

    pygame.display.flip()

pygame.quit()
g.ctx.release()
