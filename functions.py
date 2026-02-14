import random as rand
import numpy as np
import pygame
import moderngl

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
    -1: "#bf616a",
}

# Shader source code
vertex_shader = '''
#version 330

in vec2 in_vert;
in vec2 in_texcoord;
out vec2 v_texcoord;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
    v_texcoord = in_texcoord;
}
'''

fragment_shader = '''
#version 330

uniform sampler2D Texture;
uniform vec2 TextureSize;
uniform vec2 InputSize;

uniform float hardScan;
uniform float hardPix;
uniform float warpX;
uniform float warpY;
uniform float maskDark;
uniform float maskLight;
uniform float shadowMask;
uniform float brightBoost;
uniform float hardBloomPix;
uniform float hardBloomScan;
uniform float bloomAmount;
uniform float shape;

in vec2 v_texcoord;
out vec4 FragColor;

#define SourceSize vec4(TextureSize, 1.0 / TextureSize)

float ToLinear1(float c) {
    return (c <= 0.04045) ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4);
}

vec3 ToLinear(vec3 c) {
    return vec3(ToLinear1(c.r), ToLinear1(c.g), ToLinear1(c.b));
}

float ToSrgb1(float c) {
    return (c < 0.0031308 ? c * 12.92 : 1.055 * pow(c, 0.41666) - 0.055);
}

vec3 ToSrgb(vec3 c) {
    return vec3(ToSrgb1(c.r), ToSrgb1(c.g), ToSrgb1(c.b));
}

vec3 Fetch(vec2 pos, vec2 off) {
    pos = (floor(pos * SourceSize.xy + off) + vec2(0.5, 0.5)) / SourceSize.xy;
    return ToLinear(brightBoost * texture(Texture, pos.xy).rgb);
}

vec2 Dist(vec2 pos) {
    pos = pos * SourceSize.xy;
    return -((pos - floor(pos)) - vec2(0.5));
}

float Gaus(float pos, float scale) {
    return exp2(scale * pow(abs(pos), shape));
}

vec3 Horz3(vec2 pos, float off) {
    vec3 b = Fetch(pos, vec2(-1.0, off));
    vec3 c = Fetch(pos, vec2(0.0, off));
    vec3 d = Fetch(pos, vec2(1.0, off));
    float dst = Dist(pos).x;
    float scale = hardPix;
    float wb = Gaus(dst - 1.0, scale);
    float wc = Gaus(dst + 0.0, scale);
    float wd = Gaus(dst + 1.0, scale);
    return (b * wb + c * wc + d * wd) / (wb + wc + wd);
}

vec3 Horz5(vec2 pos, float off) {
    vec3 a = Fetch(pos, vec2(-2.0, off));
    vec3 b = Fetch(pos, vec2(-1.0, off));
    vec3 c = Fetch(pos, vec2(0.0, off));
    vec3 d = Fetch(pos, vec2(1.0, off));
    vec3 e = Fetch(pos, vec2(2.0, off));
    float dst = Dist(pos).x;
    float scale = hardPix;
    float wa = Gaus(dst - 2.0, scale);
    float wb = Gaus(dst - 1.0, scale);
    float wc = Gaus(dst + 0.0, scale);
    float wd = Gaus(dst + 1.0, scale);
    float we = Gaus(dst + 2.0, scale);
    return (a * wa + b * wb + c * wc + d * wd + e * we) / (wa + wb + wc + wd + we);
}

vec3 Horz7(vec2 pos, float off) {
    vec3 a = Fetch(pos, vec2(-3.0, off));
    vec3 b = Fetch(pos, vec2(-2.0, off));
    vec3 c = Fetch(pos, vec2(-1.0, off));
    vec3 d = Fetch(pos, vec2(0.0, off));
    vec3 e = Fetch(pos, vec2(1.0, off));
    vec3 f = Fetch(pos, vec2(2.0, off));
    vec3 g = Fetch(pos, vec2(3.0, off));
    float dst = Dist(pos).x;
    float scale = hardBloomPix;
    float wa = Gaus(dst - 3.0, scale);
    float wb = Gaus(dst - 2.0, scale);
    float wc = Gaus(dst - 1.0, scale);
    float wd = Gaus(dst + 0.0, scale);
    float we = Gaus(dst + 1.0, scale);
    float wf = Gaus(dst + 2.0, scale);
    float wg = Gaus(dst + 3.0, scale);
    return (a * wa + b * wb + c * wc + d * wd + e * we + f * wf + g * wg) / (wa + wb + wc + wd + we + wf + wg);
}

float Scan(vec2 pos, float off) {
    float dst = Dist(pos).y;
    return Gaus(dst + off, hardScan);
}

float BloomScan(vec2 pos, float off) {
    float dst = Dist(pos).y;
    return Gaus(dst + off, hardBloomScan);
}

vec3 Tri(vec2 pos) {
    vec3 a = Horz3(pos, -1.0);
    vec3 b = Horz5(pos, 0.0);
    vec3 c = Horz3(pos, 1.0);
    float wa = Scan(pos, -1.0);
    float wb = Scan(pos, 0.0);
    float wc = Scan(pos, 1.0);
    return (a * wa + b * wb + c * wc) / (wa + wb + wc);
}

vec3 Bloom(vec2 pos) {
    vec3 a = Horz5(pos, -2.0);
    vec3 b = Horz7(pos, -1.0);
    vec3 c = Horz7(pos, 0.0);
    vec3 d = Horz7(pos, 1.0);
    vec3 e = Horz5(pos, 2.0);
    float wa = BloomScan(pos, -2.0);
    float wb = BloomScan(pos, -1.0);
    float wc = BloomScan(pos, 0.0);
    float wd = BloomScan(pos, 1.0);
    float we = BloomScan(pos, 2.0);
    return a * wa + b * wb + c * wc + d * wd + e * we;
}

vec2 Warp(vec2 pos) {
    pos = pos * 2.0 - 1.0;
    pos *= vec2(1.0 + (pos.y * pos.y) * warpX, 1.0 + (pos.x * pos.x) * warpY);
    return pos * 0.5 + 0.5;
}

vec3 Mask(vec2 pos) {
    vec3 mask = vec3(maskDark, maskDark, maskDark);

    // Aperture-grille (vertical RGB stripes - like Trinitron)
    if (shadowMask == 2.0) {
        pos.x = fract(pos.x * 0.333333333);
        if (pos.x < 0.333) mask.r = maskLight;
        else if (pos.x < 0.666) mask.g = maskLight;
        else mask.b = maskLight;
    }
    // Stretched VGA style shadow mask (diagonal RGB pattern)
    else if (shadowMask == 3.0) {
        pos.x += pos.y * 3.0;
        pos.x = fract(pos.x * 0.166666666);
        if (pos.x < 0.333) mask.r = maskLight;
        else if (pos.x < 0.666) mask.g = maskLight;
        else mask.b = maskLight;
    }
    // VGA style shadow mask (grid pattern)
    else if (shadowMask == 4.0) {
        pos.xy = floor(pos.xy * vec2(1.0, 0.5));
        pos.x += pos.y * 3.0;
        pos.x = fract(pos.x * 0.166666666);
        if (pos.x < 0.333) mask.r = maskLight;
        else if (pos.x < 0.666) mask.g = maskLight;
        else mask.b = maskLight;
    }

    return mask;
}

void main() {
    vec2 pos = Warp(v_texcoord * (TextureSize / InputSize)) * (InputSize / TextureSize);
    vec3 outColor = Tri(pos);
    outColor.rgb += Bloom(pos) * bloomAmount;

    if (shadowMask > 0.0)
        outColor.rgb *= Mask(gl_FragCoord.xy * 1.000001);

    // Horizontal scanlines - 2px dark / 2px bright bands
    float sl = step(2.0, mod(gl_FragCoord.y, 4.0));
    outColor.rgb *= mix(0.5, 1.0, sl);

    FragColor = vec4(ToSrgb(outColor.rgb), 1.0);
}
'''

# --- Game logic functions ---

def newNum(grid, excluded=None):
    empty = list(zip(*np.where(grid == 0)))
    if excluded:
        empty = [(r, c) for r, c in empty if (r, c) not in excluded]
    if empty:
        r, c = rand.choice(empty)
        grid[r][c] = 2
        return (r, c)
    return None

def newBomb(grid):
    """Spawn a bomb tile (-1) instead of a regular tile"""
    empty = list(zip(*np.where(grid == 0)))
    if empty:
        r, c = rand.choice(empty)
        grid[r][c] = -1
        return (r, c)
    return None

def moveLeft(grid, r, c):
    moves = []
    merges = []
    bomb_destroyed = set()

    for i in range(r):
        row = [(x, j) for j, x in enumerate(grid[i]) if x != 0]

        if not row:
            continue

        new_row = []

        j = 0
        target_col = 0
        while j < len(row):
            value, orig_col = row[j]

            if value == -1:
                if j < len(row) - 1:
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    if row[j + 1][1] != target_col:
                        moves.append((i, row[j + 1][1], i, target_col, row[j + 1][0]))
                    bomb_destroyed.add((i, target_col))
                    j += 2
                else:
                    new_row.append(value)
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    j += 1
                    target_col += 1
            elif j < len(row) - 1 and row[j + 1][0] == -1:
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j + 1][1] != target_col:
                    moves.append((i, row[j + 1][1], i, target_col, row[j + 1][0]))
                bomb_destroyed.add((i, target_col))
                j += 2
            elif j < len(row) - 1 and value == row[j + 1][0] and value > 0:
                new_value = value * 2
                new_row.append(new_value)

                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j + 1][1] != target_col:
                    moves.append((i, row[j + 1][1], i, target_col, row[j + 1][0]))

                merges.append((i, target_col, new_value))
                j += 2
                target_col += 1
            else:
                new_row.append(value)
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                j += 1
                target_col += 1

        grid[i] = new_row + [0] * (c - len(new_row))

    return moves, merges, bomb_destroyed

def moveRight(grid, r, c):
    moves = []
    merges = []
    bomb_destroyed = set()

    for i in range(r):
        row = [(x, j) for j, x in enumerate(grid[i]) if x != 0]

        if not row:
            continue

        new_row = []

        j = len(row) - 1
        target_col = c - 1
        while j >= 0:
            value, orig_col = row[j]

            if value == -1:
                if j > 0:
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    if row[j - 1][1] != target_col:
                        moves.append((i, row[j - 1][1], i, target_col, row[j - 1][0]))
                    bomb_destroyed.add((i, target_col))
                    j -= 2
                else:
                    new_row.insert(0, value)
                    if orig_col != target_col:
                        moves.append((i, orig_col, i, target_col, value))
                    j -= 1
                    target_col -= 1
            elif j > 0 and row[j - 1][0] == -1:
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j - 1][1] != target_col:
                    moves.append((i, row[j - 1][1], i, target_col, row[j - 1][0]))
                bomb_destroyed.add((i, target_col))
                j -= 2
            elif j > 0 and value == row[j - 1][0] and value > 0:
                new_value = value * 2
                new_row.insert(0, new_value)

                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                if row[j - 1][1] != target_col:
                    moves.append((i, row[j - 1][1], i, target_col, row[j - 1][0]))

                merges.append((i, target_col, new_value))
                j -= 2
                target_col -= 1
            else:
                new_row.insert(0, value)
                if orig_col != target_col:
                    moves.append((i, orig_col, i, target_col, value))
                j -= 1
                target_col -= 1

        grid[i] = [0] * (c - len(new_row)) + new_row

    return moves, merges, bomb_destroyed

def moveUp(grid, r, c):
    moves = []
    merges = []
    bomb_destroyed = set()

    for col in range(c):
        column = [(grid[row][col], row) for row in range(r) if grid[row][col] != 0]

        if not column:
            continue

        new_column = []

        i = 0
        target_row = 0
        while i < len(column):
            value, orig_row = column[i]

            if value == -1:
                if i < len(column) - 1:
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    if column[i + 1][1] != target_row:
                        moves.append((column[i + 1][1], col, target_row, col, column[i + 1][0]))
                    bomb_destroyed.add((target_row, col))
                    i += 2
                else:
                    new_column.append(value)
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    i += 1
                    target_row += 1
            elif i < len(column) - 1 and column[i + 1][0] == -1:
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i + 1][1] != target_row:
                    moves.append((column[i + 1][1], col, target_row, col, column[i + 1][0]))
                bomb_destroyed.add((target_row, col))
                i += 2
            elif i < len(column) - 1 and value == column[i + 1][0] and value > 0:
                new_value = value * 2
                new_column.append(new_value)

                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i + 1][1] != target_row:
                    moves.append((column[i + 1][1], col, target_row, col, column[i + 1][0]))

                merges.append((target_row, col, new_value))
                i += 2
                target_row += 1
            else:
                new_column.append(value)
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                i += 1
                target_row += 1

        for row in range(r):
            grid[row][col] = new_column[row] if row < len(new_column) else 0

    return moves, merges, bomb_destroyed

def moveDown(grid, r, c):
    moves = []
    merges = []
    bomb_destroyed = set()

    for col in range(c):
        column = [(grid[row][col], row) for row in range(r) if grid[row][col] != 0]

        if not column:
            continue

        new_column = []

        i = len(column) - 1
        target_row = r - 1
        while i >= 0:
            value, orig_row = column[i]

            if value == -1:
                if i > 0:
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    if column[i - 1][1] != target_row:
                        moves.append((column[i - 1][1], col, target_row, col, column[i - 1][0]))
                    bomb_destroyed.add((target_row, col))
                    i -= 2
                else:
                    new_column.insert(0, value)
                    if orig_row != target_row:
                        moves.append((orig_row, col, target_row, col, value))
                    i -= 1
                    target_row -= 1
            elif i > 0 and column[i - 1][0] == -1:
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i - 1][1] != target_row:
                    moves.append((column[i - 1][1], col, target_row, col, column[i - 1][0]))
                bomb_destroyed.add((target_row, col))
                i -= 2
            elif i > 0 and value == column[i - 1][0] and value > 0:
                new_value = value * 2
                new_column.insert(0, new_value)

                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                if column[i - 1][1] != target_row:
                    moves.append((column[i - 1][1], col, target_row, col, column[i - 1][0]))

                merges.append((target_row, col, new_value))
                i -= 2
                target_row -= 1
            else:
                new_column.insert(0, value)
                if orig_row != target_row:
                    moves.append((orig_row, col, target_row, col, value))
                i -= 1
                target_row -= 1

        for row in range(r):
            grid[row][col] = (
                new_column[row - (r - len(new_column))] if row >= r - len(new_column) else 0
            )

    return moves, merges, bomb_destroyed

# --- Utility functions ---

def get_tile_color(value):
    return COLORS.get(value, "#2e3440")

def lerp(start, end, t):
    return start + (end - start) * t

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

# --- UI / rendering functions (all take game state `g` as first param) ---

def recalculate_positions(g):
    g.grid_width = g.cols * g.square_size
    g.grid_height = g.rows * g.square_size
    g.start_x = (g.RENDER_WIDTH - g.grid_width) // 2
    g.start_y = (g.RENDER_HEIGHT - g.grid_height) // 2
    g.menu_y = g.start_y + g.grid_height + g.ui_config['menu_spacing']
    g.button_x = g.start_x + (g.grid_width - g.button_width) // 2

def init_tile_cache(g):
    for value in list(COLORS.keys()):
        if value == 0:
            continue
        surface = pygame.Surface((g.square_size, g.square_size), pygame.SRCALPHA)
        color = pygame.Color(get_tile_color(value))
        pygame.draw.rect(surface, color, (0, 0, g.square_size, g.square_size))
        pygame.draw.rect(surface, "#d8dee9", (0, 0, g.square_size, g.square_size), g.ui_config['tile_border_width'])
        if value == -1 and g.bomb_image:
            bomb_size = int(g.square_size * g.ui_config['bomb_scale'])
            bomb_scaled = pygame.transform.scale(g.bomb_image, (bomb_size, bomb_size))
            bomb_rect = bomb_scaled.get_rect(center=(g.square_size // 2, g.square_size // 2))
            surface.blit(bomb_scaled, bomb_rect)
        else:
            text = g.font.render(str(value), True, "#eceff4")
            text_rect = text.get_rect(center=(g.square_size // 2, g.square_size // 2))
            surface.blit(text, text_rect)
        g.tile_cache[value] = surface

def get_cached_score(g, score_value):
    text = f"Score: {score_value}"
    if g._score_cache['text'] != text:
        g._score_cache['text'] = text
        g._score_cache['surface'] = g.font.render(text, True, "#eceff4")
    return g._score_cache['surface']

def prepare_tile_surface(g, value, scale):
    if scale == 1.0 and value in g.tile_cache:
        return g.tile_cache[value]
    scaled_size = max(int(g.square_size * scale), 1)
    if value in g.tile_cache:
        return pygame.transform.smoothscale(g.tile_cache[value], (scaled_size, scaled_size))
    surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
    color = pygame.Color(get_tile_color(value))
    pygame.draw.rect(surface, color, (0, 0, scaled_size, scaled_size))
    pygame.draw.rect(surface, "#d8dee9", (0, 0, scaled_size, scaled_size), g.ui_config['tile_border_width'])
    if value == -1 and g.bomb_image:
        bsz = int(scaled_size * g.ui_config['bomb_scale'])
        bomb_s = pygame.transform.scale(g.bomb_image, (bsz, bsz))
        bomb_r = bomb_s.get_rect(center=(scaled_size // 2, scaled_size // 2))
        surface.blit(bomb_s, bomb_r)
    elif value != 0:
        text = g.font.render(str(value), True, "#eceff4")
        text_r = text.get_rect(center=(scaled_size // 2, scaled_size // 2))
        surface.blit(text, text_r)
    return surface

def toggle_fullscreen(g):
    g.is_fullscreen = not g.is_fullscreen

    if g.is_fullscreen:
        g.screen = pygame.display.set_mode((g.NATIVE_WIDTH, g.NATIVE_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN)
        g.display_width, g.display_height = g.NATIVE_WIDTH, g.NATIVE_HEIGHT
    else:
        g.screen = pygame.display.set_mode((g.WINDOW_WIDTH, g.WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF)
        g.display_width, g.display_height = g.WINDOW_WIDTH, g.WINDOW_HEIGHT

    g.ctx = moderngl.create_context()
    g.fbo = g.ctx.framebuffer(color_attachments=[g.ctx.texture((g.display_width, g.display_height), 4)])

def start_grid_expansion(g):
    g.expand_old_sx = g.start_x
    g.expand_old_sy = g.start_y
    g.expand_old_rows = g.rows
    g.expand_old_cols = g.cols

    g.expand_direction = rand.choice(["up", "down", "left", "right"])

    if g.expand_direction in ("up", "down"):
        g.rows += 1
    else:
        g.cols += 1

    new_grid = np.zeros((g.rows, g.cols), dtype=int)

    if g.expand_direction == "down":
        new_grid[:g.expand_old_rows, :g.expand_old_cols] = g.playingGrid
    elif g.expand_direction == "up":
        new_grid[1:, :g.expand_old_cols] = g.playingGrid
    elif g.expand_direction == "right":
        new_grid[:g.expand_old_rows, :g.expand_old_cols] = g.playingGrid
    elif g.expand_direction == "left":
        new_grid[:g.expand_old_rows, 1:] = g.playingGrid

    g.playingGrid = new_grid
    g.playingGridLast = g.playingGrid.copy()

    recalculate_positions(g)

    g.grid_expanding = True
    g.expand_progress = 0

    print(f"Grid expanded to {g.rows}x{g.cols}! (direction: {g.expand_direction})")

def process_move(g, direction):
    if g.animating:
        return

    grid_before = g.playingGrid.copy()

    if direction == "up":
        moves, merges, bomb_destroyed = moveUp(g.playingGrid, g.rows, g.cols)
    elif direction == "down":
        moves, merges, bomb_destroyed = moveDown(g.playingGrid, g.rows, g.cols)
    elif direction == "left":
        moves, merges, bomb_destroyed = moveLeft(g.playingGrid, g.rows, g.cols)
    elif direction == "right":
        moves, merges, bomb_destroyed = moveRight(g.playingGrid, g.rows, g.cols)

    if np.array_equal(grid_before, g.playingGrid):
        return

    points_gained = sum(value for _, _, value in merges)

    if moves or merges:
        g.animating = True
        g.animation_progress = 0
        g.moving_tiles = [(sr, sc, er, ec, val, 0) for sr, sc, er, ec, val in moves]
        g.merging_tiles = [(r, c, val, 1.0) for r, c, val in merges]

        new_pos = newNum(g.playingGrid, excluded=bomb_destroyed)

        if new_pos:
            g.new_tile_pos = new_pos
            g.new_tile_scale = 0
            r, c = new_pos
            if g.playingGrid[r][c] > 0:
                points_gained += g.playingGrid[r][c]

        g.points += points_gained

        if any(val == g.tarExpand for _, _, val in merges) or (new_pos and g.playingGrid[new_pos[0]][new_pos[1]] == g.tarExpand):
            g.pending_expand = True
            g.tarExpand *= 2

        g.playingGridLast = g.playingGrid.copy()
        print()
        print(f"Score: {g.points} (+{points_gained})")

def update_animations(g, dt):
    if g.grid_expanding:
        g.expand_progress += g.expand_speed
        if g.expand_progress >= 1.0:
            g.grid_expanding = False
            g.expand_progress = 0
        return

    if not g.animating:
        return

    g.animation_progress += g.animation_speed

    eased_progress = ease_out_cubic(min(g.animation_progress, 1.0))
    g.moving_tiles = [(sr, sc, er, ec, val, eased_progress) for sr, sc, er, ec, val, _ in g.moving_tiles]

    if g.animation_progress > 0.6:
        merge_progress = (g.animation_progress - 0.6) / 0.4
        for i, (r, c, val, _) in enumerate(g.merging_tiles):
            if merge_progress < 0.5:
                scale = 1.0 + merge_progress * 0.4
            else:
                scale = 1.2 - (merge_progress - 0.5) * 0.4
            g.merging_tiles[i] = (r, c, val, scale)

    if g.new_tile_pos and g.animation_progress > 0.7:
        g.new_tile_scale = min((g.animation_progress - 0.7) / 0.3, 1.0)

    if g.animation_progress >= 1.0:
        g.animating = False
        g.moving_tiles = []
        g.merging_tiles = []
        g.new_tile_pos = None
        g.new_tile_scale = 0
        if g.pending_expand:
            g.pending_expand = False
            start_grid_expansion(g)

def draw_tile(g, r, c, value, scale=1.0, alpha=255):
    x = g.start_x + c * g.square_size
    y = g.start_y + r * g.square_size

    if scale == 1.0 and alpha == 255 and value in g.tile_cache:
        g.render_surface.blit(g.tile_cache[value], (x, y))
        return

    scaled_size = max(int(g.square_size * scale), 1)
    offset = (g.square_size - scaled_size) / 2

    if value in g.tile_cache:
        tile_surface = pygame.transform.smoothscale(g.tile_cache[value], (scaled_size, scaled_size))
    else:
        tile_surface = pygame.Surface((scaled_size, scaled_size), pygame.SRCALPHA)
        color = pygame.Color(get_tile_color(value))
        color.a = alpha
        pygame.draw.rect(tile_surface, color, (0, 0, scaled_size, scaled_size))
        pygame.draw.rect(tile_surface, "#d8dee9", (0, 0, scaled_size, scaled_size), g.ui_config['tile_border_width'])
        if value == -1 and g.bomb_image:
            bomb_size = int(scaled_size * g.ui_config['bomb_scale'])
            bomb_scaled = pygame.transform.scale(g.bomb_image, (bomb_size, bomb_size))
            bomb_rect = bomb_scaled.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(bomb_scaled, bomb_rect)
        elif value != 0:
            text = g.font.render(str(value), True, "#eceff4")
            text_rect = text.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(text, text_rect)

    if alpha != 255:
        tile_surface.set_alpha(alpha)

    g.render_surface.blit(tile_surface, (x + offset, y + offset))

def draw_button(g, x, y, width, height, text, cost, can_afford, active=False):
    if can_afford and not active:
        color = "#81a1c1"
        hover_color = "#88c0d0"
    elif active:
        color = "#a3be8c"
        hover_color = "#a3be8c"
    else:
        color = "#4c566a"
        hover_color = "#4c566a"

    mouse_pos = pygame.mouse.get_pos()
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    is_hover = x <= mouse_x <= x + width and y <= mouse_y <= y + height

    button_color = hover_color if is_hover else color

    pygame.draw.rect(g.render_surface, button_color, (x, y, width, height))
    pygame.draw.rect(g.render_surface, "#d8dee9", (x, y, width, height), 3)

    if active:
        button_text = g.small_font.render("ACTIVE", True, "#eceff4")
    else:
        button_text = g.small_font.render(text, True, "#eceff4")
    text_rect = button_text.get_rect(center=(x + width//2, y + height//3))
    g.render_surface.blit(button_text, text_rect)

    if not active:
        cost_color = "#a3be8c" if can_afford else "#bf616a"
        cost_text = g.small_font.render(f"Cost: {cost}", True, cost_color)
        cost_rect = cost_text.get_rect(center=(x + width//2, y + 2*height//3))
        g.render_surface.blit(cost_text, cost_rect)

    return is_hover and can_afford and not active

def handle_button_click(g, mouse_pos):
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    button_y = g.menu_y + 30
    if g.button_x <= mouse_x <= g.button_x + g.button_width and button_y <= mouse_y <= button_y + g.button_height:
        if g.points >= g.bomb_ability_cost and not g.selecting_bomb_position:
            g.points -= g.bomb_ability_cost
            g.selecting_bomb_position = True
            print(f"Bomb ability activated! Click an empty tile to place the bomb. Score: {g.points}")

def get_tile_from_mouse(g, mouse_pos):
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    if g.start_x <= mouse_x <= g.start_x + g.grid_width and g.start_y <= mouse_y <= g.start_y + g.grid_height:
        c = int((mouse_x - g.start_x) // g.square_size)
        r = int((mouse_y - g.start_y) // g.square_size)

        if 0 <= r < g.rows and 0 <= c < g.cols:
            return (r, c)

    return None

def place_bomb_at_tile(g, r, c):
    if g.playingGrid[r][c] == 0:
        g.playingGrid[r][c] = -1
        g.selecting_bomb_position = False

        g.animating = True
        g.animation_progress = 0.7
        g.new_tile_pos = (r, c)
        g.new_tile_scale = 0

        print(f"Bomb placed at position ({r}, {c})")

def render_to_opengl(g):
    texture_data = pygame.image.tostring(g.render_surface, 'RGB', True)

    g.prog['TextureSize'].value = (g.RENDER_WIDTH, g.RENDER_HEIGHT)
    g.prog['InputSize'].value = (g.RENDER_WIDTH, g.RENDER_HEIGHT)
    g.prog['hardScan'].value = g.crt_params['hardScan']
    g.prog['hardPix'].value = g.crt_params['hardPix']
    g.prog['warpX'].value = g.crt_params['warpX']
    g.prog['warpY'].value = g.crt_params['warpY']
    g.prog['maskDark'].value = g.crt_params['maskDark']
    g.prog['maskLight'].value = g.crt_params['maskLight']
    g.prog['shadowMask'].value = g.crt_params['shadowMask']
    g.prog['brightBoost'].value = g.crt_params['brightBoost']
    g.prog['hardBloomPix'].value = g.crt_params['hardBloomPix']
    g.prog['hardBloomScan'].value = g.crt_params['hardBloomScan']
    g.prog['bloomAmount'].value = g.crt_params['bloomAmount']
    g.prog['shape'].value = g.crt_params['shape']

    g.texture.write(texture_data)

    g.ctx.clear(0.0, 0.0, 0.0)
    g.texture.use(0)
    g.prog['Texture'].value = 0
    g.vao.render(moderngl.TRIANGLE_STRIP)
