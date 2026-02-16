import pygame
import numpy as np
import functions as func
import moderngl
import game2048_engine as engine

pygame.init()

class G: pass
g = G()

g.NATIVE_WIDTH = 1920
g.NATIVE_HEIGHT = 1200
g.RENDER_WIDTH = 3840
g.RENDER_HEIGHT = 2400
g.WINDOW_WIDTH = 1280
g.WINDOW_HEIGHT = 800
g.is_fullscreen = False

g.screen = pygame.display.set_mode((g.WINDOW_WIDTH, g.WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
g.display_width, g.display_height = g.WINDOW_WIDTH, g.WINDOW_HEIGHT
pygame.display.set_caption("A Little Slow Test")

g.ctx = moderngl.create_context()
g.render_surface = pygame.Surface((g.RENDER_WIDTH, g.RENDER_HEIGHT))

clock = pygame.time.Clock()

pygame.font.init()
g.font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 29)
g.small_font = pygame.font.Font("fonts/pixelOperatorBold.ttf", 20)

g.ui_config = {
    'square_size': 150,
    'initial_rows': 2,
    'initial_cols': 4,
    'menu_height': 150,
    'menu_spacing': 90,
    'button_width': 200,
    'button_height': 60,
    'grid_border_width': 2,
    'tile_border_width': 2,
    'bomb_scale': 0.8,
    'score_x': 50,
    'score_y': 50,
}

g.rows, g.cols = 2, 4
g.square_size = g.ui_config['square_size']

g.grid_width = 0
g.grid_height = 0
g.start_x = 0
g.start_y = 0
g.menu_y = 0
g.button_x = 0
g.button_width = g.ui_config['button_width']
g.button_height = g.ui_config['button_height']
g.menu_height = g.ui_config['menu_height']

func.recalculate_positions(g)

# Create engine and clear the auto-spawned tiles
g.engine = engine.GameEngine(2, 4)
for r in range(2):
    for c in range(4):
        g.engine.set_tile(r, c, 0)

# Place test tiles: slow 2 at (0,0), regular 2 at (1,3)
g.engine.set_tile(0, 0, 2, int(engine.PassiveType.A_LITTLE_SLOW))
g.engine.set_tile(1, 3, 2)

g.playingGrid = np.array(g.engine.get_grid_values(), dtype=int).reshape(g.rows, g.cols)
g.points = g.engine.score()
g.passive_map = {(r, c): ptype for r, c, ptype in g.engine.get_passive_map()}

g.pending_passives = []
g.passive_menu_open = False
g.passive_menu_tile = None

g.abilities = [
    {'name': 'Bomb', 'cost': 750, 'charges': 0, 'description': 'Destroy a tile'},
    {'name': 'Freeze', 'cost': 500, 'charges': 0, 'description': 'Hold tile 1 turn'},
]
g.selecting_bomb_position = False
g.selecting_freeze_position = False
g.frozen_tiles = set()
g.hovered_tile = None

g.bomb_image = None
g.shop_open = False
g.pending_shop = False
try:
    g.bomb_image = pygame.image.load("assets/sprites/bomb.png")
    bomb_size = int(g.square_size * g.ui_config['bomb_scale'])
    g.bomb_image = pygame.transform.scale(g.bomb_image, (bomb_size, bomb_size))
except:
    pass

g.animating = False
g.animation_progress = 0
g.animation_speed = 0.15
g.moving_tiles = []
g.merging_tiles = []
g.new_tile_pos = None
g.new_tile_scale = 0

g.grid_expanding = False
g.expand_progress = 0
g.expand_speed = 0.03
g.pending_expand = False
g.expand_old_rows = 0
g.expand_old_cols = 0
g.expand_old_sx = 0
g.expand_old_sy = 0
g.expand_direction = ""

g.tile_cache = {}
g._score_cache = {'text': None, 'surface': None}
func.init_tile_cache(g)

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

g.prog = g.ctx.program(vertex_shader=func.vertex_shader, fragment_shader=func.fragment_shader)

vertices = np.array([
    -1.0, -1.0,  0.0, 0.0,
     1.0, -1.0,  1.0, 0.0,
    -1.0,  1.0,  0.0, 1.0,
     1.0,  1.0,  1.0, 1.0,
], dtype='f4')

vbo = g.ctx.buffer(vertices.tobytes())
g.vao = g.ctx.simple_vertex_array(g.prog, vbo, 'in_vert', 'in_texcoord')

g.texture = g.ctx.texture((g.RENDER_WIDTH, g.RENDER_HEIGHT), 3)
g.texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
g.texture.repeat_x = False
g.texture.repeat_y = False

g.fbo = g.ctx.framebuffer(color_attachments=[g.ctx.texture((g.display_width, g.display_height), 4)])

def test_process_move(g, direction):
    if g.animating:
        return

    result = g.engine.process_move(direction)

    if not result.board_changed:
        return

    # Remove spawned tile
    sr, sc = result.spawned_tile
    if sr >= 0:
        g.engine.set_tile(sr, sc, 0)

    func.sync_grid_from_engine(g)

    g.animating = True
    g.animation_progress = 0
    g.moving_tiles = [(m.start_row, m.start_col, m.end_row, m.end_col, m.value, 0)
                      for m in result.moves]
    g.merging_tiles = [(m.row, m.col, m.new_value, 1.0) for m in result.merges]

    for u in result.slow_mover_updates:
        if u.old_row != u.new_row or u.old_col != u.new_col:
            g.moving_tiles.append((u.old_row, u.old_col, u.new_row, u.new_col, u.value, 0))

    g.new_tile_pos = None
    g.new_tile_scale = 0

    g.pending_passives = [(c.row, c.col, c.tile_value) for c in result.passive_candidates]
    g.frozen_tiles.clear()

running = True
while running:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and not g.animating:
            match event.key:
                case pygame.K_UP:
                    test_process_move(g, "up")
                case pygame.K_DOWN:
                    test_process_move(g, "down")
                case pygame.K_LEFT:
                    test_process_move(g, "left")
                case pygame.K_RIGHT:
                    test_process_move(g, "right")
                case pygame.K_ESCAPE:
                    running = False

    func.update_animations(g, dt)

    g.render_surface.fill(func.COLORS[0])

    score_text = func.get_cached_score(g, g.points)
    g.render_surface.blit(score_text, (g.ui_config['score_x'], g.ui_config['score_y']))

    for r in range(g.rows):
        for c in range(g.cols):
            x = g.start_x + c * g.square_size
            y = g.start_y + r * g.square_size
            pygame.draw.rect(g.render_surface, func.UI_COLORS['border'],
                           (x, y, g.square_size, g.square_size), g.ui_config['grid_border_width'])

    if not g.animating:
        for r in range(g.rows):
            for c in range(g.cols):
                value = g.playingGrid[r][c]
                if value:
                    func.draw_tile(g, r, c, value)
                    if (r, c) in g.passive_map:
                        func.draw_passive_indicator(g, r, c)
    else:
        merging_positions = {(r, c) for r, c, _, _ in g.merging_tiles}

        for r in range(g.rows):
            for c in range(g.cols):
                value = g.playingGrid[r][c]
                if value and (r, c) not in merging_positions and (r, c) != g.new_tile_pos:
                    is_moving_destination = any(er == r and ec == c for _, _, er, ec, _, _ in g.moving_tiles)
                    if not is_moving_destination or g.animation_progress >= 1.0:
                        func.draw_tile(g, r, c, value)
                        if (r, c) in g.passive_map:
                            func.draw_passive_indicator(g, r, c)

        for sr, sc, er, ec, val, progress in g.moving_tiles:
            r_pos = func.lerp(sr, er, progress)
            c_pos = func.lerp(sc, ec, progress)
            func.draw_tile(g, r_pos, c_pos, val)

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

        if g.new_tile_pos and g.new_tile_scale > 0:
            nr, nc = g.new_tile_pos
            nscale = func.ease_out_cubic(g.new_tile_scale)
            surface = func.prepare_tile_surface(g, g.playingGrid[nr][nc], nscale)
            if surface:
                x = g.start_x + nc * g.square_size
                y = g.start_y + nr * g.square_size
                offset = (g.square_size - surface.get_width()) / 2
                g.render_surface.blit(surface, (x + offset, y + offset))

    for (fr, fc) in g.frozen_tiles:
        if 0 <= fr < g.rows and 0 <= fc < g.cols and g.playingGrid[fr][fc] != 0:
            fx = g.start_x + fc * g.square_size
            fy = g.start_y + fr * g.square_size
            tint = pygame.Surface((g.square_size, g.square_size), pygame.SRCALPHA)
            tint.fill((100, 160, 220, 80))
            g.render_surface.blit(tint, (fx, fy))

    if not g.animating:
        mouse_pos = pygame.mouse.get_pos()
        hovered = func.get_tile_from_mouse(g, mouse_pos)
        if hovered and hovered in g.passive_map:
            func.draw_passive_tooltip(g, hovered[0], hovered[1], g.passive_map[hovered])

    func.render_to_opengl(g)
    pygame.display.flip()

pygame.quit()
g.ctx.release()
