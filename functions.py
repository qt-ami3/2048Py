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

def _get_segments(size, frozen_positions):
    """Split a range into segments separated by frozen positions."""
    segments = []
    seg_start = None
    for idx in range(size):
        if idx in frozen_positions:
            if seg_start is not None:
                segments.append((seg_start, idx))
                seg_start = None
        else:
            if seg_start is None:
                seg_start = idx
    if seg_start is not None:
        segments.append((seg_start, size))
    return segments

def _process_segment_left(tiles, row_idx, seg_start, moves, merges, bomb_destroyed):
    """Process a segment of tiles compacting left. Returns list of result values."""
    new_vals = []
    j = 0
    target = seg_start
    while j < len(tiles):
        value, orig = tiles[j]

        if value == -1:
            if j < len(tiles) - 1:
                if orig != target:
                    moves.append((row_idx, orig, row_idx, target, value))
                if tiles[j + 1][1] != target:
                    moves.append((row_idx, tiles[j + 1][1], row_idx, target, tiles[j + 1][0]))
                bomb_destroyed.add((row_idx, target))
                j += 2
            else:
                new_vals.append(value)
                if orig != target:
                    moves.append((row_idx, orig, row_idx, target, value))
                j += 1
                target += 1
        elif j < len(tiles) - 1 and tiles[j + 1][0] == -1:
            if orig != target:
                moves.append((row_idx, orig, row_idx, target, value))
            if tiles[j + 1][1] != target:
                moves.append((row_idx, tiles[j + 1][1], row_idx, target, tiles[j + 1][0]))
            bomb_destroyed.add((row_idx, target))
            j += 2
        elif j < len(tiles) - 1 and value == tiles[j + 1][0] and value > 0:
            new_value = value * 2
            new_vals.append(new_value)
            if orig != target:
                moves.append((row_idx, orig, row_idx, target, value))
            if tiles[j + 1][1] != target:
                moves.append((row_idx, tiles[j + 1][1], row_idx, target, tiles[j + 1][0]))
            merges.append((row_idx, target, new_value))
            j += 2
            target += 1
        else:
            new_vals.append(value)
            if orig != target:
                moves.append((row_idx, orig, row_idx, target, value))
            j += 1
            target += 1
    return new_vals

def _process_segment_right(tiles, row_idx, seg_end, moves, merges, bomb_destroyed):
    """Process a segment of tiles compacting right. Returns list of result values (left to right)."""
    new_vals = []
    j = len(tiles) - 1
    target = seg_end - 1
    while j >= 0:
        value, orig = tiles[j]

        if value == -1:
            if j > 0:
                if orig != target:
                    moves.append((row_idx, orig, row_idx, target, value))
                if tiles[j - 1][1] != target:
                    moves.append((row_idx, tiles[j - 1][1], row_idx, target, tiles[j - 1][0]))
                bomb_destroyed.add((row_idx, target))
                j -= 2
            else:
                new_vals.insert(0, value)
                if orig != target:
                    moves.append((row_idx, orig, row_idx, target, value))
                j -= 1
                target -= 1
        elif j > 0 and tiles[j - 1][0] == -1:
            if orig != target:
                moves.append((row_idx, orig, row_idx, target, value))
            if tiles[j - 1][1] != target:
                moves.append((row_idx, tiles[j - 1][1], row_idx, target, tiles[j - 1][0]))
            bomb_destroyed.add((row_idx, target))
            j -= 2
        elif j > 0 and value == tiles[j - 1][0] and value > 0:
            new_value = value * 2
            new_vals.insert(0, new_value)
            if orig != target:
                moves.append((row_idx, orig, row_idx, target, value))
            if tiles[j - 1][1] != target:
                moves.append((row_idx, tiles[j - 1][1], row_idx, target, tiles[j - 1][0]))
            merges.append((row_idx, target, new_value))
            j -= 2
            target -= 1
        else:
            new_vals.insert(0, value)
            if orig != target:
                moves.append((row_idx, orig, row_idx, target, value))
            j -= 1
            target -= 1
    return new_vals

def moveLeft(grid, r, c, frozen=set()):
    moves = []
    merges = []
    bomb_destroyed = set()

    for i in range(r):
        frozen_cols = {fc for fr, fc in frozen if fr == i}
        segments = _get_segments(c, frozen_cols)

        for seg_start, seg_end in segments:
            seg_tiles = [(grid[i][j], j) for j in range(seg_start, seg_end) if grid[i][j] != 0]
            new_vals = _process_segment_left(seg_tiles, i, seg_start, moves, merges, bomb_destroyed) if seg_tiles else []
            for idx, col in enumerate(range(seg_start, seg_end)):
                grid[i][col] = new_vals[idx] if idx < len(new_vals) else 0

    return moves, merges, bomb_destroyed

def moveRight(grid, r, c, frozen=set()):
    moves = []
    merges = []
    bomb_destroyed = set()

    for i in range(r):
        frozen_cols = {fc for fr, fc in frozen if fr == i}
        segments = _get_segments(c, frozen_cols)

        for seg_start, seg_end in segments:
            seg_tiles = [(grid[i][j], j) for j in range(seg_start, seg_end) if grid[i][j] != 0]
            new_vals = _process_segment_right(seg_tiles, i, seg_end, moves, merges, bomb_destroyed) if seg_tiles else []
            seg_len = seg_end - seg_start
            for idx, col in enumerate(range(seg_start, seg_end)):
                right_idx = idx - (seg_len - len(new_vals))
                grid[i][col] = new_vals[right_idx] if right_idx >= 0 else 0

    return moves, merges, bomb_destroyed

def _process_segment_up(tiles, col_idx, seg_start, moves, merges, bomb_destroyed):
    """Process a segment of tiles compacting up. Returns list of result values."""
    new_vals = []
    i = 0
    target = seg_start
    while i < len(tiles):
        value, orig = tiles[i]

        if value == -1:
            if i < len(tiles) - 1:
                if orig != target:
                    moves.append((orig, col_idx, target, col_idx, value))
                if tiles[i + 1][1] != target:
                    moves.append((tiles[i + 1][1], col_idx, target, col_idx, tiles[i + 1][0]))
                bomb_destroyed.add((target, col_idx))
                i += 2
            else:
                new_vals.append(value)
                if orig != target:
                    moves.append((orig, col_idx, target, col_idx, value))
                i += 1
                target += 1
        elif i < len(tiles) - 1 and tiles[i + 1][0] == -1:
            if orig != target:
                moves.append((orig, col_idx, target, col_idx, value))
            if tiles[i + 1][1] != target:
                moves.append((tiles[i + 1][1], col_idx, target, col_idx, tiles[i + 1][0]))
            bomb_destroyed.add((target, col_idx))
            i += 2
        elif i < len(tiles) - 1 and value == tiles[i + 1][0] and value > 0:
            new_value = value * 2
            new_vals.append(new_value)
            if orig != target:
                moves.append((orig, col_idx, target, col_idx, value))
            if tiles[i + 1][1] != target:
                moves.append((tiles[i + 1][1], col_idx, target, col_idx, tiles[i + 1][0]))
            merges.append((target, col_idx, new_value))
            i += 2
            target += 1
        else:
            new_vals.append(value)
            if orig != target:
                moves.append((orig, col_idx, target, col_idx, value))
            i += 1
            target += 1
    return new_vals

def _process_segment_down(tiles, col_idx, seg_end, moves, merges, bomb_destroyed):
    """Process a segment of tiles compacting down. Returns list of result values (top to bottom)."""
    new_vals = []
    i = len(tiles) - 1
    target = seg_end - 1
    while i >= 0:
        value, orig = tiles[i]

        if value == -1:
            if i > 0:
                if orig != target:
                    moves.append((orig, col_idx, target, col_idx, value))
                if tiles[i - 1][1] != target:
                    moves.append((tiles[i - 1][1], col_idx, target, col_idx, tiles[i - 1][0]))
                bomb_destroyed.add((target, col_idx))
                i -= 2
            else:
                new_vals.insert(0, value)
                if orig != target:
                    moves.append((orig, col_idx, target, col_idx, value))
                i -= 1
                target -= 1
        elif i > 0 and tiles[i - 1][0] == -1:
            if orig != target:
                moves.append((orig, col_idx, target, col_idx, value))
            if tiles[i - 1][1] != target:
                moves.append((tiles[i - 1][1], col_idx, target, col_idx, tiles[i - 1][0]))
            bomb_destroyed.add((target, col_idx))
            i -= 2
        elif i > 0 and value == tiles[i - 1][0] and value > 0:
            new_value = value * 2
            new_vals.insert(0, new_value)
            if orig != target:
                moves.append((orig, col_idx, target, col_idx, value))
            if tiles[i - 1][1] != target:
                moves.append((tiles[i - 1][1], col_idx, target, col_idx, tiles[i - 1][0]))
            merges.append((target, col_idx, new_value))
            i -= 2
            target -= 1
        else:
            new_vals.insert(0, value)
            if orig != target:
                moves.append((orig, col_idx, target, col_idx, value))
            i -= 1
            target -= 1
    return new_vals

def moveUp(grid, r, c, frozen=set()):
    moves = []
    merges = []
    bomb_destroyed = set()

    for col in range(c):
        frozen_rows = {fr for fr, fc in frozen if fc == col}
        segments = _get_segments(r, frozen_rows)

        for seg_start, seg_end in segments:
            seg_tiles = [(grid[row][col], row) for row in range(seg_start, seg_end) if grid[row][col] != 0]
            new_vals = _process_segment_up(seg_tiles, col, seg_start, moves, merges, bomb_destroyed) if seg_tiles else []
            for idx, row in enumerate(range(seg_start, seg_end)):
                grid[row][col] = new_vals[idx] if idx < len(new_vals) else 0

    return moves, merges, bomb_destroyed

def moveDown(grid, r, c, frozen=set()):
    moves = []
    merges = []
    bomb_destroyed = set()

    for col in range(c):
        frozen_rows = {fr for fr, fc in frozen if fc == col}
        segments = _get_segments(r, frozen_rows)

        for seg_start, seg_end in segments:
            seg_tiles = [(grid[row][col], row) for row in range(seg_start, seg_end) if grid[row][col] != 0]
            new_vals = _process_segment_down(seg_tiles, col, seg_end, moves, merges, bomb_destroyed) if seg_tiles else []
            seg_len = seg_end - seg_start
            for idx, row in enumerate(range(seg_start, seg_end)):
                down_idx = idx - (seg_len - len(new_vals))
                grid[row][col] = new_vals[down_idx] if down_idx >= 0 else 0

    return moves, merges, bomb_destroyed

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

    g.pending_shop = True
    print(f"Grid expanded to {g.rows}x{g.cols}! (direction: {g.expand_direction})")

def process_move(g, direction):
    if g.animating:
        return

    grid_before = g.playingGrid.copy()

    frozen = g.frozen_tiles.copy()

    if direction == "up":
        moves, merges, bomb_destroyed = moveUp(g.playingGrid, g.rows, g.cols, frozen)
    elif direction == "down":
        moves, merges, bomb_destroyed = moveDown(g.playingGrid, g.rows, g.cols, frozen)
    elif direction == "left":
        moves, merges, bomb_destroyed = moveLeft(g.playingGrid, g.rows, g.cols, frozen)
    elif direction == "right":
        moves, merges, bomb_destroyed = moveRight(g.playingGrid, g.rows, g.cols, frozen)

    if np.array_equal(grid_before, g.playingGrid):
        return

    # Freeze wears off after one move
    g.frozen_tiles.clear()

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
            if g.pending_shop:
                g.pending_shop = False
                g.shop_open = True
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

def draw_button(g, x, y, width, height, text, charges, enabled, active=False):
    if enabled and not active:
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
        charge_color = "#a3be8c" if charges > 0 else "#bf616a"
        charge_text = g.small_font.render(f"Charges: {charges}", True, charge_color)
        charge_rect = charge_text.get_rect(center=(x + width//2, y + 2*height//3))
        g.render_surface.blit(charge_text, charge_rect)

    return is_hover and enabled and not active

def handle_button_click(g, mouse_pos):
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    # Match the two-button layout computed in main.py
    button_gap = 20
    total_w = g.button_width * 2 + button_gap
    btn_left_x = g.start_x + (g.grid_width - total_w) // 2
    btn_right_x = btn_left_x + g.button_width + button_gap
    btn_y = g.menu_y + 30

    # Bomb button (left)
    if btn_left_x <= mouse_x <= btn_left_x + g.button_width and btn_y <= mouse_y <= btn_y + g.button_height:
        if g.abilities[0]['charges'] > 0 and not g.selecting_bomb_position and not g.selecting_freeze_position:
            g.abilities[0]['charges'] -= 1
            g.selecting_bomb_position = True
            print(f"Bomb ability activated! Charges remaining: {g.abilities[0]['charges']}")
        return

    # Freeze button (right)
    if btn_right_x <= mouse_x <= btn_right_x + g.button_width and btn_y <= mouse_y <= btn_y + g.button_height:
        if g.abilities[1]['charges'] > 0 and not g.selecting_freeze_position and not g.selecting_bomb_position:
            g.abilities[1]['charges'] -= 1
            g.selecting_freeze_position = True
            print(f"Freeze ability activated! Charges remaining: {g.abilities[1]['charges']}")
        return

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

def place_freeze_on_tile(g, r, c):
    if g.playingGrid[r][c] > 0 and (r, c) not in g.frozen_tiles:
        g.frozen_tiles.add((r, c))
        g.selecting_freeze_position = False
        print(f"Tile at ({r}, {c}) frozen for 1 turn")

def draw_shop(g):
    """Render the shop popup panel with semi-transparent overlay."""
    # Semi-transparent dark overlay
    overlay = pygame.Surface((g.RENDER_WIDTH, g.RENDER_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    g.render_surface.blit(overlay, (0, 0))

    # Panel dimensions
    panel_w, panel_h = 800, 600
    panel_x = (g.RENDER_WIDTH - panel_w) // 2
    panel_y = (g.RENDER_HEIGHT - panel_h) // 2

    # Panel background
    pygame.draw.rect(g.render_surface, "#3b4252", (panel_x, panel_y, panel_w, panel_h))
    pygame.draw.rect(g.render_surface, "#d8dee9", (panel_x, panel_y, panel_w, panel_h), 3)

    # Title
    title = g.font.render("SHOP", True, "#eceff4")
    title_rect = title.get_rect(center=(g.RENDER_WIDTH // 2, panel_y + 40))
    g.render_surface.blit(title, title_rect)

    # Score display
    score_text = g.small_font.render(f"Score: {g.points}", True, "#a3be8c")
    score_rect = score_text.get_rect(center=(g.RENDER_WIDTH // 2, panel_y + 80))
    g.render_surface.blit(score_text, score_rect)

    # Ability rows
    row_y_start = panel_y + 130
    row_height = 80

    # Get mouse position in render coordinates for hover effects
    mouse_pos = pygame.mouse.get_pos()
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    for i, ability in enumerate(g.abilities):
        y = row_y_start + i * row_height

        # Ability name + description
        name_text = g.font.render(ability['name'], True, "#eceff4")
        g.render_surface.blit(name_text, (panel_x + 30, y))
        desc_text = g.small_font.render(ability['description'], True, "#d8dee9")
        g.render_surface.blit(desc_text, (panel_x + 30, y + 32))

        # Cost per charge
        cost_text = g.small_font.render(f"{ability['cost']}pts ea.", True, "#88c0d0")
        g.render_surface.blit(cost_text, (panel_x + 350, y + 10))

        # - button
        btn_size = 40
        minus_x = panel_x + 560
        btn_y = y + 10

        minus_hover = minus_x <= mouse_x <= minus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size
        minus_color = "#bf616a" if minus_hover and ability['charges'] > 0 else "#4c566a"
        pygame.draw.rect(g.render_surface, minus_color, (minus_x, btn_y, btn_size, btn_size))
        pygame.draw.rect(g.render_surface, "#d8dee9", (minus_x, btn_y, btn_size, btn_size), 2)
        minus_text = g.font.render("-", True, "#eceff4")
        minus_rect = minus_text.get_rect(center=(minus_x + btn_size // 2, btn_y + btn_size // 2))
        g.render_surface.blit(minus_text, minus_rect)

        # Charges count
        qty_text = g.font.render(str(ability['charges']), True, "#eceff4")
        qty_rect = qty_text.get_rect(center=(minus_x + btn_size + 35, btn_y + btn_size // 2))
        g.render_surface.blit(qty_text, qty_rect)

        # + button
        plus_x = minus_x + btn_size + 70
        can_add = g.points >= ability['cost']

        plus_hover = plus_x <= mouse_x <= plus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size
        plus_color = "#a3be8c" if plus_hover and can_add else "#4c566a"
        pygame.draw.rect(g.render_surface, plus_color, (plus_x, btn_y, btn_size, btn_size))
        pygame.draw.rect(g.render_surface, "#d8dee9", (plus_x, btn_y, btn_size, btn_size), 2)
        plus_text = g.font.render("+", True, "#eceff4")
        plus_rect = plus_text.get_rect(center=(plus_x + btn_size // 2, btn_y + btn_size // 2))
        g.render_surface.blit(plus_text, plus_rect)

    # Divider line
    div_y = panel_y + panel_h - 100
    pygame.draw.line(g.render_surface, "#d8dee9", (panel_x + 30, div_y), (panel_x + panel_w - 30, div_y), 2)

    # DONE button (centered)
    done_w, done_h = 160, 50
    done_x = (g.RENDER_WIDTH - done_w) // 2
    done_y = div_y + 25

    done_hover = done_x <= mouse_x <= done_x + done_w and done_y <= mouse_y <= done_y + done_h
    done_color = "#a3be8c" if done_hover else "#5e81ac"
    pygame.draw.rect(g.render_surface, done_color, (done_x, done_y, done_w, done_h))
    pygame.draw.rect(g.render_surface, "#d8dee9", (done_x, done_y, done_w, done_h), 2)
    done_text = g.font.render("DONE", True, "#eceff4")
    done_rect = done_text.get_rect(center=(done_x + done_w // 2, done_y + done_h // 2))
    g.render_surface.blit(done_text, done_rect)

    # Store layout info for click handling
    g._shop_layout = {
        'row_y_start': row_y_start, 'row_height': row_height,
        'btn_size': btn_size, 'minus_x': minus_x,
        'plus_x_offset': btn_size + 70,
        'done_rect': (done_x, done_y, done_w, done_h),
    }


def handle_shop_click(g, mouse_pos):
    """Process clicks in the shop panel. +/- apply immediately."""
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    layout = getattr(g, '_shop_layout', None)
    if not layout:
        return

    btn_size = layout['btn_size']
    minus_x = layout['minus_x']

    for i, ability in enumerate(g.abilities):
        btn_y = layout['row_y_start'] + i * layout['row_height'] + 10

        # Minus button — refund a charge
        if minus_x <= mouse_x <= minus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size:
            if ability['charges'] > 0:
                ability['charges'] -= 1
                g.points += ability['cost']
            return

        # Plus button — buy a charge immediately
        plus_x = minus_x + layout['plus_x_offset']
        if plus_x <= mouse_x <= plus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size:
            if g.points >= ability['cost']:
                g.points -= ability['cost']
                ability['charges'] += 1
            return

    # Done button
    dx, dy, dw, dh = layout['done_rect']
    if dx <= mouse_x <= dx + dw and dy <= mouse_y <= dy + dh:
        g.shop_open = False
        print(f"Shop closed. Score: {g.points}")
        return


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
