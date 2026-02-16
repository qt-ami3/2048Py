#2048Squared (title pending) copyright (c) 2026 River Knuuttila, common alias: Annie Valentine or aval. All Rights Reserved.
#Do not redistribute or reuse code without accrediting and explicit permission from author.
#Contact:
#+1 (808) 223 4780
#riverknuuttila2@outlook.com

import random as rand
import numpy as np
import pygame
import moderngl
import game2048_engine as engine

# Color schemes for different expansion levels
DEFAULT_COLORS = {
    0: "#2e3440",
    2: "#5e81ac",
    4: "#81a1c1",
    8: "#88c0d0",
    16: "#8fbcbb",
    32: "#a3be8c",
    64: "#ebcb8b",
    128: "#d08770",
    256: "#bf616a",
    512: "#b48ead",
    1024: "#4c566a",
    2048: "#5e81ac",
    4096: "#81a1c1",
    8192: "#88c0d0",
    16384: "#8fbcbb",
    -1: "#bf616a",
}

GRUVBOX_COLORS = {
    0: "#3c3836",
    2: "#83a598",
    4: "#458588",
    8: "#b8bb26",
    16: "#98971a",
    32: "#d79921",
    64: "#d65d0e",
    128: "#cc241d",
    256: "#b16286",
    512: "#689d6a",
    1024: "#8ec07c",
    2048: "#fb4934",
    4096: "#fe8019",
    8192: "#fabd2f",
    16384: "#b8bb26",
    32768: "#83a598",
    -1: "#cc241d",
}

NORD_COLORS = {
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
    4096: "#d08770",
    8192: "#b48ead",
    16384: "#88c0d0",
    32768: "#81a1c1",
    -1: "#bf616a",
}

TOKYO_NIGHT_COLORS = {
    0: "#1a1b26",
    2: "#7dcfff",
    4: "#2ac3de",
    8: "#7aa2f7",
    16: "#bb9af7",
    32: "#c0caf5",
    64: "#9ece6a",
    128: "#73daca",
    256: "#e0af68",
    512: "#ff9e64",
    1024: "#f7768e",
    2048: "#bb9af7",
    4096: "#7aa2f7",
    8192: "#ff9e64",
    16384: "#7dcfff",
    32768: "#bb9af7",
    -1: "#f7768e",
}

# UI color schemes for each theme
GRUVBOX_UI = {
    'background': "#282828",
    'border': "#ebdbb2",
    'text': "#fbf1c7",
    'text_dim': "#d5c4a1",
    'button_normal': "#458588",
    'button_hover': "#83a598",
    'button_active': "#98971a",
    'button_disabled': "#3c3836",
    'accent_green': "#b8bb26",
    'accent_red': "#fb4934",
    'accent_blue': "#83a598",
    'overlay': "#1d2021",
    'panel': "#3c3836",
}

NORD_UI = {
    'background': "#2e3440",
    'border': "#d8dee9",
    'text': "#eceff4",
    'text_dim': "#d8dee9",
    'button_normal': "#81a1c1",
    'button_hover': "#88c0d0",
    'button_active': "#a3be8c",
    'button_disabled': "#4c566a",
    'accent_green': "#a3be8c",
    'accent_red': "#bf616a",
    'accent_blue': "#88c0d0",
    'overlay': "#3b4252",
    'panel': "#3b4252",
}

TOKYO_NIGHT_UI = {
    'background': "#1a1b26",
    'border': "#7aa2f7",
    'text': "#c0caf5",
    'text_dim': "#a9b1d6",
    'button_normal': "#7aa2f7",
    'button_hover': "#7dcfff",
    'button_active': "#9ece6a",
    'button_disabled': "#24283b",
    'accent_green': "#9ece6a",
    'accent_red': "#f7768e",
    'accent_blue': "#7dcfff",
    'overlay': "#1f2335",
    'panel': "#24283b",
}

# Active color scheme (starts with Gruvbox at tarExpand=2048)
COLORS = {**GRUVBOX_COLORS}
UI_COLORS = {**GRUVBOX_UI}

# Color transition state
_color_transition = {
    'active': False,
    'progress': 0.0,
    'speed': 0.015,  # Transition speed (0.015 = ~67 frames for full transition at 60fps)
    'old_colors': None,
    'new_colors': None,
    'old_ui_colors': None,
    'new_ui_colors': None,
    'cache_rebuild_counter': 0,
}

def get_color_scheme_for_expansion(tar_expand):
    if tar_expand > 4096:
        return TOKYO_NIGHT_COLORS, TOKYO_NIGHT_UI
    elif tar_expand > 2048:
        return NORD_COLORS, NORD_UI
    else:
        return GRUVBOX_COLORS, GRUVBOX_UI

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

# --- Utility functions ---

def get_tile_color(value):
    if value in COLORS:
        return COLORS[value]
    if value > 0:
        keys = sorted([k for k in COLORS.keys() if k > 0 and k != -1])
        if keys:
            idx = len([k for k in keys if k <= value]) % len(keys)
            return COLORS[keys[idx]]
    return COLORS.get(0, "#2e3440")

def update_color_scheme(g):
    new_colors, new_ui_colors = get_color_scheme_for_expansion(g.engine.tar_expand())

    if COLORS != new_colors:
        _color_transition['active'] = True
        _color_transition['progress'] = 0.0
        _color_transition['old_colors'] = {**COLORS}
        _color_transition['new_colors'] = new_colors
        _color_transition['old_ui_colors'] = {**UI_COLORS}
        _color_transition['new_ui_colors'] = new_ui_colors

        scheme_name = "Unknown"
        if new_colors == GRUVBOX_COLORS:
            scheme_name = "Gruvbox"
        elif new_colors == NORD_COLORS:
            scheme_name = "Nord"
        elif new_colors == TOKYO_NIGHT_COLORS:
            scheme_name = "Tokyo Night"

        print(f"\n*** Transitioning to {scheme_name} color scheme... ***\n")

def lerp(start, end, t):
    return start + (end - start) * t

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

def lerp_color(color1, color2, t):
    c1 = pygame.Color(color1)
    c2 = pygame.Color(color2)
    r = int(lerp(c1.r, c2.r, t))
    g = int(lerp(c1.g, c2.g, t))
    b = int(lerp(c1.b, c2.b, t))
    return f"#{r:02x}{g:02x}{b:02x}"

# --- UI / rendering functions ---

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
        pygame.draw.rect(surface, UI_COLORS['border'], (0, 0, g.square_size, g.square_size), g.ui_config['tile_border_width'])
        if value == -1 and g.bomb_image:
            bomb_size = int(g.square_size * g.ui_config['bomb_scale'])
            bomb_scaled = pygame.transform.scale(g.bomb_image, (bomb_size, bomb_size))
            bomb_rect = bomb_scaled.get_rect(center=(g.square_size // 2, g.square_size // 2))
            surface.blit(bomb_scaled, bomb_rect)
        else:
            text = g.font.render(str(value), True, UI_COLORS['text'])
            text_rect = text.get_rect(center=(g.square_size // 2, g.square_size // 2))
            surface.blit(text, text_rect)
        g.tile_cache[value] = surface

def get_cached_score(g, score_value):
    text = f"Score: {score_value}"
    if g._score_cache['text'] != text or _color_transition['active']:
        g._score_cache['text'] = text
        g._score_cache['surface'] = g.font.render(text, True, UI_COLORS['text'])
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
    pygame.draw.rect(surface, UI_COLORS['border'], (0, 0, scaled_size, scaled_size), g.ui_config['tile_border_width'])
    if value == -1 and g.bomb_image:
        bsz = int(scaled_size * g.ui_config['bomb_scale'])
        bomb_s = pygame.transform.scale(g.bomb_image, (bsz, bsz))
        bomb_r = bomb_s.get_rect(center=(scaled_size // 2, scaled_size // 2))
        surface.blit(bomb_s, bomb_r)
    elif value != 0:
        text = g.font.render(str(value), True, UI_COLORS['text'])
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

def sync_grid_from_engine(g):
    g.rows = g.engine.rows()
    g.cols = g.engine.cols()
    g.playingGrid = np.array(g.engine.get_grid_values(), dtype=int).reshape(g.rows, g.cols)
    g.points = g.engine.score()
    g.passive_map = {(r, c): ptype for r, c, ptype in g.engine.get_passive_map()}

def process_move(g, direction):
    if g.animating:
        return

    result = g.engine.process_move(direction)

    if not result.board_changed:
        return

    sync_grid_from_engine(g)

    g.animating = True
    g.animation_progress = 0
    g.moving_tiles = [(m.start_row, m.start_col, m.end_row, m.end_col, m.value, 0)
                      for m in result.moves]
    g.merging_tiles = [(m.row, m.col, m.new_value, 1.0) for m in result.merges]

    # Slow mover updates animate as single-cell moves
    for u in result.slow_mover_updates:
        if u.old_row != u.new_row or u.old_col != u.new_col:
            g.moving_tiles.append((u.old_row, u.old_col, u.new_row, u.new_col, u.value, 0))

    if result.spawned_tile[0] >= 0:
        g.new_tile_pos = tuple(result.spawned_tile)
        g.new_tile_scale = 0

    if result.should_expand:
        g.pending_expand = True
        update_color_scheme(g)

    # Queue passive candidates for menu
    g.pending_passives = [(c.row, c.col, c.tile_value) for c in result.passive_candidates]

    g.frozen_tiles.clear()

    print()
    print(f"Score: {g.points} (+{result.points_gained})")

def start_grid_expansion(g):
    g.expand_old_sx = g.start_x
    g.expand_old_sy = g.start_y
    g.expand_old_rows = g.rows
    g.expand_old_cols = g.cols

    g.expand_direction = rand.choice(["up", "down", "left", "right"])

    # Tell the C++ engine to expand the board
    g.engine.complete_expansion(g.expand_direction)
    sync_grid_from_engine(g)
    recalculate_positions(g)

    g.grid_expanding = True
    g.expand_progress = 0

    g.pending_shop = True
    print(f"Grid expanded to {g.rows}x{g.cols}! (direction: {g.expand_direction})")

def place_bomb_at_tile(g, r, c):
    if g.playingGrid[r][c] == 0:
        g.engine.place_bomb(r, c)
        sync_grid_from_engine(g)
        g.selecting_bomb_position = False

        g.animating = True
        g.animation_progress = 0.7
        g.new_tile_pos = (r, c)
        g.new_tile_scale = 0

        print(f"Bomb placed at position ({r}, {c})")

def place_freeze_on_tile(g, r, c):
    if g.playingGrid[r][c] > 0 and (r, c) not in g.frozen_tiles:
        g.engine.place_freeze(r, c)
        g.frozen_tiles.add((r, c))
        g.selecting_freeze_position = False
        print(f"Tile at ({r}, {c}) frozen for 1 turn")

def update_color_transition(g):
    if not _color_transition['active']:
        return False

    _color_transition['progress'] += _color_transition['speed']

    if _color_transition['progress'] >= 1.0:
        _color_transition['progress'] = 1.0
        _color_transition['active'] = False

    t = ease_out_cubic(_color_transition['progress'])

    old_colors = _color_transition['old_colors']
    new_colors = _color_transition['new_colors']

    for key in new_colors.keys():
        if key in old_colors:
            COLORS[key] = lerp_color(old_colors[key], new_colors[key], t)
        else:
            COLORS[key] = new_colors[key]

    old_ui = _color_transition['old_ui_colors']
    new_ui = _color_transition['new_ui_colors']

    for key in new_ui.keys():
        if key in old_ui:
            UI_COLORS[key] = lerp_color(old_ui[key], new_ui[key], t)
        else:
            UI_COLORS[key] = new_ui[key]

    _color_transition['cache_rebuild_counter'] += 1
    if _color_transition['cache_rebuild_counter'] >= 3 or not _color_transition['active']:
        _color_transition['cache_rebuild_counter'] = 0
        init_tile_cache(g)

    return _color_transition['active']

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
        elif g.pending_passives:
            open_next_passive_menu(g)

def open_next_passive_menu(g):
    if g.pending_passives:
        r, c, val = g.pending_passives[0]
        g.passive_menu_tile = (r, c)
        g.passive_menu_open = True

def handle_passive_menu_click(g, mouse_pos):
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    layout = getattr(g, '_passive_menu_layout', None)
    if not layout:
        return

    for i, (btn_x, btn_y, btn_w, btn_h, passive_type) in enumerate(layout['buttons']):
        if btn_x <= mouse_x <= btn_x + btn_w and btn_y <= mouse_y <= btn_y + btn_h:
            r, c = g.passive_menu_tile
            g.engine.assign_passive(r, c, passive_type)
            sync_grid_from_engine(g)
            g.passive_menu_open = False
            g.pending_passives.pop(0)
            print(f"Assigned '{engine.passive_name(engine.PassiveType(passive_type))}' to tile at ({r}, {c})")

            if g.pending_passives:
                open_next_passive_menu(g)
            return

def draw_passive_menu(g):
    overlay = pygame.Surface((g.RENDER_WIDTH, g.RENDER_HEIGHT), pygame.SRCALPHA)
    overlay_color = pygame.Color(UI_COLORS['overlay'])
    overlay.fill((overlay_color.r, overlay_color.g, overlay_color.b, 160))
    g.render_surface.blit(overlay, (0, 0))

    panel_w, panel_h = 700, 400
    panel_x = (g.RENDER_WIDTH - panel_w) // 2
    panel_y = (g.RENDER_HEIGHT - panel_h) // 2

    pygame.draw.rect(g.render_surface, UI_COLORS['panel'], (panel_x, panel_y, panel_w, panel_h))
    pygame.draw.rect(g.render_surface, UI_COLORS['border'], (panel_x, panel_y, panel_w, panel_h), 3)

    # Title
    title = g.font.render("PASSIVE ABILITY", True, UI_COLORS['text'])
    title_rect = title.get_rect(center=(g.RENDER_WIDTH // 2, panel_y + 40))
    g.render_surface.blit(title, title_rect)

    # Show which tile
    r, c = g.passive_menu_tile
    tile_val = g.playingGrid[r][c]
    tile_text = g.small_font.render(f"Select a passive for tile [{tile_val}] at ({r}, {c})", True, UI_COLORS['text_dim'])
    tile_rect = tile_text.get_rect(center=(g.RENDER_WIDTH // 2, panel_y + 80))
    g.render_surface.blit(tile_text, tile_rect)

    # Get mouse position
    mouse_pos = pygame.mouse.get_pos()
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    # Passive option buttons
    available_passives = [
        (int(engine.PassiveType.A_LITTLE_SLOW),
         engine.passive_name(engine.PassiveType.A_LITTLE_SLOW),
         engine.passive_description(engine.PassiveType.A_LITTLE_SLOW)),
    ]

    buttons = []
    btn_w, btn_h = 600, 70
    btn_start_y = panel_y + 130

    for i, (ptype, pname, pdesc) in enumerate(available_passives):
        btn_x = (g.RENDER_WIDTH - btn_w) // 2
        btn_y = btn_start_y + i * (btn_h + 15)

        is_hover = btn_x <= mouse_x <= btn_x + btn_w and btn_y <= mouse_y <= btn_y + btn_h
        btn_color = UI_COLORS['button_hover'] if is_hover else UI_COLORS['button_normal']

        pygame.draw.rect(g.render_surface, btn_color, (btn_x, btn_y, btn_w, btn_h))
        pygame.draw.rect(g.render_surface, UI_COLORS['border'], (btn_x, btn_y, btn_w, btn_h), 2)

        name_surf = g.font.render(pname, True, UI_COLORS['text'])
        g.render_surface.blit(name_surf, (btn_x + 15, btn_y + 8))

        desc_surf = g.small_font.render(pdesc, True, UI_COLORS['text_dim'])
        g.render_surface.blit(desc_surf, (btn_x + 15, btn_y + 38))

        buttons.append((btn_x, btn_y, btn_w, btn_h, ptype))

    g._passive_menu_layout = {'buttons': buttons}

def draw_passive_indicator(g, r, c):
    dot_x = g.start_x + c * g.square_size + g.square_size // 2
    dot_y = g.start_y + r * g.square_size + g.square_size - 12
    pygame.draw.circle(g.render_surface, UI_COLORS['accent_green'], (dot_x, dot_y), 5)

def draw_passive_tooltip(g, r, c, passive_type):
    ptype = engine.PassiveType(passive_type)
    name = engine.passive_name(ptype)
    desc = engine.passive_description(ptype)

    mouse_pos = pygame.mouse.get_pos()
    mx = int(mouse_pos[0] * g.RENDER_WIDTH / g.display_width)
    my = int(mouse_pos[1] * g.RENDER_HEIGHT / g.display_height)

    name_surf = g.small_font.render(name, True, UI_COLORS['text'])
    desc_surf = g.small_font.render(desc, True, UI_COLORS['text_dim'])

    tw = max(name_surf.get_width(), desc_surf.get_width()) + 20
    th = name_surf.get_height() + desc_surf.get_height() + 15

    tx = mx + 15
    ty = my - th - 10
    if tx + tw > g.RENDER_WIDTH:
        tx = mx - tw - 15
    if ty < 0:
        ty = my + 20

    tooltip = pygame.Surface((tw, th), pygame.SRCALPHA)
    panel_color = pygame.Color(UI_COLORS['panel'])
    tooltip.fill((panel_color.r, panel_color.g, panel_color.b, 220))
    border_color = pygame.Color(UI_COLORS['border'])
    pygame.draw.rect(tooltip, (border_color.r, border_color.g, border_color.b, 220), (0, 0, tw, th), 2)

    tooltip.blit(name_surf, (10, 5))
    tooltip.blit(desc_surf, (10, name_surf.get_height() + 10))

    g.render_surface.blit(tooltip, (tx, ty))

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
        pygame.draw.rect(tile_surface, UI_COLORS['border'], (0, 0, scaled_size, scaled_size), g.ui_config['tile_border_width'])
        if value == -1 and g.bomb_image:
            bomb_size = int(scaled_size * g.ui_config['bomb_scale'])
            bomb_scaled = pygame.transform.scale(g.bomb_image, (bomb_size, bomb_size))
            bomb_rect = bomb_scaled.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(bomb_scaled, bomb_rect)
        elif value != 0:
            text = g.font.render(str(value), True, UI_COLORS['text'])
            text_rect = text.get_rect(center=(scaled_size // 2, scaled_size // 2))
            tile_surface.blit(text, text_rect)

    if alpha != 255:
        tile_surface.set_alpha(alpha)

    g.render_surface.blit(tile_surface, (x + offset, y + offset))

def draw_button(g, x, y, width, height, text, charges, enabled, active=False):
    if enabled and not active:
        color = UI_COLORS['button_normal']
        hover_color = UI_COLORS['button_hover']
    elif active:
        color = UI_COLORS['button_active']
        hover_color = UI_COLORS['button_active']
    else:
        color = UI_COLORS['button_disabled']
        hover_color = UI_COLORS['button_disabled']

    mouse_pos = pygame.mouse.get_pos()
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    is_hover = x <= mouse_x <= x + width and y <= mouse_y <= y + height

    button_color = hover_color if is_hover else color

    pygame.draw.rect(g.render_surface, button_color, (x, y, width, height))
    pygame.draw.rect(g.render_surface, UI_COLORS['border'], (x, y, width, height), 3)

    if active:
        button_text = g.small_font.render("ACTIVE", True, UI_COLORS['text'])
    else:
        button_text = g.small_font.render(text, True, UI_COLORS['text'])
    text_rect = button_text.get_rect(center=(x + width//2, y + height//3))
    g.render_surface.blit(button_text, text_rect)

    if not active:
        charge_color = UI_COLORS['accent_green'] if charges > 0 else UI_COLORS['accent_red']
        charge_text = g.small_font.render(f"Charges: {charges}", True, charge_color)
        charge_rect = charge_text.get_rect(center=(x + width//2, y + 2*height//3))
        g.render_surface.blit(charge_text, charge_rect)

    return is_hover and enabled and not active

def handle_button_click(g, mouse_pos):
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

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

def draw_shop(g):
    overlay = pygame.Surface((g.RENDER_WIDTH, g.RENDER_HEIGHT), pygame.SRCALPHA)
    overlay_color = pygame.Color(UI_COLORS['overlay'])
    overlay.fill((overlay_color.r, overlay_color.g, overlay_color.b, 160))
    g.render_surface.blit(overlay, (0, 0))

    panel_w, panel_h = 800, 600
    panel_x = (g.RENDER_WIDTH - panel_w) // 2
    panel_y = (g.RENDER_HEIGHT - panel_h) // 2

    pygame.draw.rect(g.render_surface, UI_COLORS['panel'], (panel_x, panel_y, panel_w, panel_h))
    pygame.draw.rect(g.render_surface, UI_COLORS['border'], (panel_x, panel_y, panel_w, panel_h), 3)

    title = g.font.render("SHOP", True, UI_COLORS['text'])
    title_rect = title.get_rect(center=(g.RENDER_WIDTH // 2, panel_y + 40))
    g.render_surface.blit(title, title_rect)

    score_text = g.small_font.render(f"Score: {g.points}", True, UI_COLORS['accent_green'])
    score_rect = score_text.get_rect(center=(g.RENDER_WIDTH // 2, panel_y + 80))
    g.render_surface.blit(score_text, score_rect)

    row_y_start = panel_y + 130
    row_height = 80

    mouse_pos = pygame.mouse.get_pos()
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    for i, ability in enumerate(g.abilities):
        y = row_y_start + i * row_height

        name_text = g.font.render(ability['name'], True, UI_COLORS['text'])
        g.render_surface.blit(name_text, (panel_x + 30, y))
        desc_text = g.small_font.render(ability['description'], True, UI_COLORS['text_dim'])
        g.render_surface.blit(desc_text, (panel_x + 30, y + 32))

        cost_text = g.small_font.render(f"{ability['cost']}pts ea.", True, UI_COLORS['accent_blue'])
        g.render_surface.blit(cost_text, (panel_x + 350, y + 10))

        btn_size = 40
        minus_x = panel_x + 560
        btn_y = y + 10

        minus_hover = minus_x <= mouse_x <= minus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size
        minus_color = UI_COLORS['accent_red'] if minus_hover and ability['charges'] > 0 else UI_COLORS['button_disabled']
        pygame.draw.rect(g.render_surface, minus_color, (minus_x, btn_y, btn_size, btn_size))
        pygame.draw.rect(g.render_surface, UI_COLORS['border'], (minus_x, btn_y, btn_size, btn_size), 2)
        minus_text = g.font.render("-", True, UI_COLORS['text'])
        minus_rect = minus_text.get_rect(center=(minus_x + btn_size // 2, btn_y + btn_size // 2))
        g.render_surface.blit(minus_text, minus_rect)

        qty_text = g.font.render(str(ability['charges']), True, UI_COLORS['text'])
        qty_rect = qty_text.get_rect(center=(minus_x + btn_size + 35, btn_y + btn_size // 2))
        g.render_surface.blit(qty_text, qty_rect)

        plus_x = minus_x + btn_size + 70
        can_add = g.points >= ability['cost']

        plus_hover = plus_x <= mouse_x <= plus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size
        plus_color = UI_COLORS['accent_green'] if plus_hover and can_add else UI_COLORS['button_disabled']
        pygame.draw.rect(g.render_surface, plus_color, (plus_x, btn_y, btn_size, btn_size))
        pygame.draw.rect(g.render_surface, UI_COLORS['border'], (plus_x, btn_y, btn_size, btn_size), 2)
        plus_text = g.font.render("+", True, UI_COLORS['text'])
        plus_rect = plus_text.get_rect(center=(plus_x + btn_size // 2, btn_y + btn_size // 2))
        g.render_surface.blit(plus_text, plus_rect)

    div_y = panel_y + panel_h - 100
    pygame.draw.line(g.render_surface, UI_COLORS['border'], (panel_x + 30, div_y), (panel_x + panel_w - 30, div_y), 2)

    done_w, done_h = 160, 50
    done_x = (g.RENDER_WIDTH - done_w) // 2
    done_y = div_y + 25

    done_hover = done_x <= mouse_x <= done_x + done_w and done_y <= mouse_y <= done_y + done_h
    done_color = UI_COLORS['button_active'] if done_hover else UI_COLORS['button_normal']
    pygame.draw.rect(g.render_surface, done_color, (done_x, done_y, done_w, done_h))
    pygame.draw.rect(g.render_surface, UI_COLORS['border'], (done_x, done_y, done_w, done_h), 2)
    done_text = g.font.render("DONE", True, UI_COLORS['text'])
    done_rect = done_text.get_rect(center=(done_x + done_w // 2, done_y + done_h // 2))
    g.render_surface.blit(done_text, done_rect)

    g._shop_layout = {
        'row_y_start': row_y_start, 'row_height': row_height,
        'btn_size': btn_size, 'minus_x': minus_x,
        'plus_x_offset': btn_size + 70,
        'done_rect': (done_x, done_y, done_w, done_h),
    }


def handle_shop_click(g, mouse_pos):
    mouse_x = mouse_pos[0] * g.RENDER_WIDTH / g.display_width
    mouse_y = mouse_pos[1] * g.RENDER_HEIGHT / g.display_height

    layout = getattr(g, '_shop_layout', None)
    if not layout:
        return

    btn_size = layout['btn_size']
    minus_x = layout['minus_x']

    for i, ability in enumerate(g.abilities):
        btn_y = layout['row_y_start'] + i * layout['row_height'] + 10

        if minus_x <= mouse_x <= minus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size:
            if ability['charges'] > 0:
                ability['charges'] -= 1
                g.points += ability['cost']
            return

        plus_x = minus_x + layout['plus_x_offset']
        if plus_x <= mouse_x <= plus_x + btn_size and btn_y <= mouse_y <= btn_y + btn_size:
            if g.points >= ability['cost']:
                g.points -= ability['cost']
                ability['charges'] += 1
            return

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
