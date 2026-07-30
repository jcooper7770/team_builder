"""
Move counts table for all pokemon

TODO:
 - [DONE] pick only meta relevant pokemon
 - [DONE] pick only meta relevant moves

  $ python -m application.pokemon.move_counts

# TODO: Figure out how to get latest rankings data from gobattlelog for new moves
"""

from dataclasses import dataclass
import json
import math
import os.path
import logging
import re
import requests
import time

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from application.utils.database import create_engine
#from ..utils.database import create_engine

logging.getLogger("PIL.PngImagePlugin").setLevel(logging.CRITICAL + 1)

HELP_TEXT = """HELP:
Fast move on top.

Charge moves:
5- -> 5/4
The "-" means that the
  second move is one less
twitch.tv/itsflippincoop"""

HELP_LINES = [
    "HOW TO READ THIS",
    "Fast move on top",
    "5-  =  5 or 4 (leftover energy)",
    "*  =  alt. 3rd cycle count",
    "twitch.tv/itsflippincoop",
]

ALL_RANKINGS = []
GAME_MASTER = {}
LATEST_DATA = {}


# ---------------------------------------------------------------------------
# THEME / RENDERING
# ---------------------------------------------------------------------------
SS = 3  # supersampling factor; everything is drawn at SS x scale then
        # downsampled at the end for smooth text and rounded corners.

BG_TOP = (13, 16, 26)
BG_BOTTOM = (20, 24, 38)
CARD_BG = (26, 31, 46)
CARD_BORDER = (45, 52, 74)
SHADOW_COLOR = (0, 0, 0)

TEXT_PRIMARY = (241, 245, 249)
#TEXT_SECONDARY = (148, 163, 184)
TEXT_SECONDARY = (148, 163, 184)
TEXT_MUTED = (100, 112, 134)

ACCENT_FAST = (56, 189, 248)      # sky-400, fast move pill
ACCENT_COUNT = (224, 219, 55)     # gold, main count numbers
ACCENT_ALT = (167, 139, 250)      # violet-300, 3rd charge move accent
DIVIDER = (42, 49, 68)

CARD_W = 224
CARD_H = 270
GAP = 16
MARGIN = 28
HEADER_H = 96
CARD_PAD = 20  # transparent margin baked into each card tile so its drop shadow isn't clipped

FONT_DIR = os.path.join("static", "fonts")


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size * SS)


def F_TITLE(size): return _font("Outfit-Bold.ttf", size)
def F_BOLD(size): return _font("Outfit-Bold.ttf", size)
def F_REG(size): return _font("Outfit-Regular.ttf", size)
def F_MONO_B(size): return _font("JetBrainsMono-Bold.ttf", size)
def F_MONO(size): return _font("JetBrainsMono-Regular.ttf", size)


def S(v):
    return v * SS


def vertical_gradient(size, top, bottom):
    """Returns an RGB image with a smooth top-to-bottom gradient."""
    w, h = size
    base = Image.new("RGB", (1, h), 0)
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h))


def rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
    """
    Draws a rounded rectangle. Uses PIL's native rounded_rectangle when
    available (Pillow >= 8.2), and falls back to manually composing it
    from rectangles + pieslices/arcs on older Pillow versions (this is
    what avoids 'ImageDraw object has no attribute rounded_rectangle'
    on servers running an older Pillow).
    """
    if hasattr(draw, "rounded_rectangle"):
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
        return

    x0, y0, x1, y1 = box
    r = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    r = max(r, 0)

    if fill is not None:
        draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        draw.pieslice([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=fill)
        draw.pieslice([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=fill)
        draw.pieslice([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=fill)
        draw.pieslice([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=fill)

    if outline is not None:
        draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
        draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
        draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
        draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)
        draw.arc([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=outline, width=width)
        draw.arc([x1 - 2 * r, y0, x1, y0 + 2 * r], 270, 360, fill=outline, width=width)
        draw.arc([x0, y1 - 2 * r, x0 + 2 * r, y1], 90, 180, fill=outline, width=width)
        draw.arc([x1 - 2 * r, y1 - 2 * r, x1, y1], 0, 90, fill=outline, width=width)


def draw_card_shadow(canvas, box, radius, blur=10, opacity=90, offset=(0, 6)):
    """Paints a soft drop shadow behind a card directly onto `canvas` (RGBA)."""
    x0, y0, x1, y1 = box
    pad = blur * 3
    shadow = Image.new("RGBA", (int(x1 - x0 + pad * 2), int(y1 - y0 + pad * 2)), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    rounded_rect(
        sd,
        [pad, pad, x1 - x0 + pad, y1 - y0 + pad],
        radius, fill=(*SHADOW_COLOR, opacity)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(shadow, (int(x0 - pad + offset[0]), int(y0 - pad + offset[1])))


def draw_text_centered(draw, cx, y, text, font, fill, tracking=0):
    """Draws horizontally centered text, with optional letter-spacing in px."""
    if tracking == 0:
        draw.text((cx, y), text, font=font, fill=fill, anchor="ma")
        return
    widths = [draw.textlength(ch, font=font) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill, anchor="la")
        x += w + tracking


def pill(draw, box, fill, outline=None, width=1):
    radius = (box[3] - box[1]) / 2
    rounded_rect(draw, box, radius, fill=fill, outline=outline, width=width)


def circular_thumb(sprite_img, diameter, ring_color, bg_color):
    """Returns an RGBA image: circular backdrop + centered sprite."""
    d = int(diameter)
    out = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)
    draw.ellipse([0, 0, d, d], fill=bg_color)
    draw.ellipse([S(1), S(1), d - S(1), d - S(1)], outline=ring_color, width=S(1))
    if sprite_img is not None:
        inner = int(d * 0.72)
        spr = sprite_img.convert("RGBA").resize((inner, inner), Image.LANCZOS)
        out.alpha_composite(spr, ((d - inner) // 2, (d - inner) // 2 - S(1)))
    return out


def draw_move_card(canvas, draw, x, y, pokemon_name, pokemon_moveset, sprite_img):
    """Draws one modern, rounded 'stat card' for a pokemon's move counts."""
    box = (S(x), S(y), S(x + CARD_W), S(y + CARD_H))
    radius = S(16)

    draw_card_shadow(canvas, box, radius, blur=S(4), opacity=70, offset=(0, S(3)))
    rounded_rect(draw, box, radius, fill=CARD_BG, outline=CARD_BORDER, width=S(1))

    cx = S(x + CARD_W / 2)

    # sprite
    thumb_d = S(100)
    thumb = circular_thumb(sprite_img, thumb_d, ring_color=DIVIDER, bg_color=(34, 40, 58, 255))
    canvas.alpha_composite(thumb, (int(cx - thumb_d / 2), int(S(y + 14))))

    # name
    name_y = S(y + 100)
    draw_text_centered(draw, cx, name_y, pokemon_name.upper(), F_BOLD(14), TEXT_PRIMARY, tracking=S(1))

    # fast move pill
    fast_text = pokemon_moveset.get("fast", "?")
    fnt_fast = F_MONO_B(13)
    fw = draw.textlength(fast_text, font=fnt_fast)
    pill_pad_x = S(12)
    pill_h = S(28)
    pill_w = fw + pill_pad_x * 2
    pill_y0 = S(y + 128)
    pill_box = (cx - pill_w / 2, pill_y0, cx + pill_w / 2, pill_y0 + pill_h)
    pill(draw, pill_box, fill=(56, 189, 248, 32), outline=ACCENT_FAST, width=int(S(1.5)))
    draw.text((cx, pill_y0 + pill_h / 2), fast_text, font=fnt_fast, fill=(214, 242, 255), anchor="mm")

    # divider
    div_y = S(y + 168)
    draw.line([(S(x + 18), div_y), (S(x + CARD_W - 18), div_y)], fill=DIVIDER, width=S(1))

    # charge moves
    charges = pokemon_moveset.get("charge", [])[:3]
    row_h = S(30)
    row_y = div_y + S(14)
    accents = [ACCENT_COUNT, ACCENT_COUNT, ACCENT_ALT]
    for i, cm in enumerate(charges):
        move_name = cm.get("move", "???")
        count = str(cm.get("count", "?"))
        ry = row_y + i * row_h
        max_w = S(CARD_W - 90)
        fnt = F_REG(13)
        while draw.textlength(move_name, font=fnt) > max_w and len(move_name) > 3:
            move_name = move_name[:-2]
        draw.text((S(x + 18), ry + row_h / 2), move_name, font=fnt, fill=TEXT_SECONDARY, anchor="lm")

        count_fnt = F_MONO_B(18)
        cw = draw.textlength(count, font=count_fnt)
        badge_w = max(cw + S(18), S(38))
        badge_h = S(26)
        bx1 = S(x + CARD_W - 18)
        bx0 = bx1 - badge_w
        by0 = ry + row_h / 2 - badge_h / 2
        by1 = by0 + badge_h
        accent = accents[i] if i < len(accents) else ACCENT_COUNT
        pill(draw, (bx0, by0, bx1, by1), fill=(*accent, 99), outline=(0,0,0), width=int(S(1.5)))
        draw.text((bx1 - badge_w / 2, ry + row_h / 2), count, font=count_fnt, fill=(0,0,0), anchor="mm")


def draw_header_card(canvas, draw, x, y, logo_img, help_lines):
    """Draws the branded header/legend card that replaces the old 'logo' cell."""
    box = (S(x), S(y), S(x + CARD_W), S(y + CARD_H))
    radius = S(16)
    draw_card_shadow(canvas, box, radius, blur=S(4), opacity=70, offset=(0, S(3)))
    rounded_rect(draw, box, radius, fill=(20, 24, 38), outline=CARD_BORDER, width=S(1))

    cx = S(x + CARD_W / 2)
    if logo_img is not None:
        d = S(72)
        logo = logo_img.convert("RGBA").resize((int(d), int(d)), Image.LANCZOS)
        canvas.alpha_composite(logo, (int(cx - d / 2), int(S(y + 14))))

    ty = S(y + 100)
    for i, line in enumerate(help_lines):
        color = TEXT_PRIMARY if i == 0 else TEXT_SECONDARY
        fnt = F_BOLD(13) if i == 0 else F_REG(12)
        draw_text_centered(draw, cx, ty, line, fnt, color)
        ty += S(20)


def render_card_tile(draw_fn, *args):
    """
    Renders one card (move card or header card) on its own small supersampled
    tile, then downsamples just that tile.

    This matters for memory: drawing the *entire* page at SS-x resolution
    (as an earlier version of this script did) means a several-thousand-pixel
    canvas that can run a low-memory server out of RAM and get silently
    killed with no traceback. Supersampling one card at a time keeps peak
    memory bounded no matter how many pokemon are in the list.
    """
    tile_w = CARD_W + 2 * CARD_PAD
    tile_h = CARD_H + 2 * CARD_PAD
    tile = Image.new("RGBA", (S(tile_w), S(tile_h)), (0, 0, 0, 0))
    tile_draw = ImageDraw.Draw(tile)
    draw_fn(tile, tile_draw, CARD_PAD, CARD_PAD, *args)
    return tile.resize((tile_w, tile_h), Image.LANCZOS)


def render_title_tile(width, height, title, subtitle):
    """Renders the page title/subtitle on its own small supersampled tile."""
    tile = Image.new("RGBA", (S(width), S(height)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    draw_text_centered(d, S(width / 2), S(0), title, F_TITLE(24), TEXT_PRIMARY, tracking=S(1))
    draw_text_centered(d, S(width / 2), S(34), subtitle, F_REG(12), TEXT_MUTED)
    return tile.resize((width, height), Image.LANCZOS)


def load_data(data):
    """
    Returns the data loaded from the db
    """
    result = json.loads(data)
    if isinstance(result, str):
        result = json.loads(result)
    return result
    

def get_popular_moves(league="GL", days_back=0):
    """
    Gets all the popular moves from the database per pokemon
    """
    global LATEST_DATA
    if not LATEST_DATA:
        engine = create_engine()
        query_results = engine.execute(f'SELECT * from `pokemon_data` WHERE pokemon_data.league="{league}";')
        results = [result for result in query_results]
        latest_data = load_data(results[0][1])
        LATEST_DATA = latest_data
    pokemon_moves = {}
    start_time = time.time()
    for record in LATEST_DATA.get('records'):
        if days_back and record.get('time') < start_time - days_back * 24 * 3600:
            continue
        for pokemon in record.get('oppo_team').split('/'):
            species, moves = pokemon.split(':')
            if species not in pokemon_moves:
                pokemon_moves[species] = {}
            for move in moves.split(','):
                pokemon_moves[species].update({move: pokemon_moves[species].get(move, 0) + 1}) 
    return pokemon_moves


def get_moves(game_master):
    """
    Get all moves from the game master

    :param game_master: The game master data
    :type game_master: dict

    :return: All moves in dict form
    :rtype: dict
    """
    all_moves = {}
    for move in game_master.get('moves', []):
        all_moves[move['moveId'].lower()] = move
    return all_moves


def get_move_counts(game_master, chosen_pokemon=None, n_moves=5):
    """
    Creates move counts dict with all pokemon

    :param game_master: The game master data
    :type game_master: dict
    :param chosen_pokemon: A single pokemon to get move counts (Default: None)
    :type chosen_pokemon: str
    :param n_moves: The number of moves to calculate (Default: 5)
    :type n_moves: int

    :return: The move counts for all pokemon
    :rtype: dict
    """
    if not game_master:
        game_master = get_game_master()
    counts = {}
    moves = get_moves(game_master)
    for pokemon in game_master.get("pokemon", []):
        species_id = pokemon.get('speciesId')
        if chosen_pokemon:
            if isinstance(chosen_pokemon, list):
                if species_id not in chosen_pokemon:
                    continue
            elif chosen_pokemon not in species_id:
                continue
        #if chosen_pokemon and chosen_pokemon not in species_id:
        #    continue
        give_return = 'shadoweligible' in pokemon.get('tags', [])
        # Skip shadow pokemon
        if "_shadow" in species_id or "_mega" in species_id:
            continue
        # Skip smeargle
        if species_id == "smeargle":
            continue
        counts[species_id] = {}
        # Go through all fast moves and get counts for all
        charge_moves = pokemon.get('chargedMoves', [])
        if give_return:
            charge_moves.append("RETURN")
        for fast_move in pokemon.get('fastMoves', []):
            # Skip hidden power moves
            #if "HIDDEN_POWER" in fast_move:
            #    continue
            move = moves[fast_move.lower()]
            if not move:
                print(f"Missing {fast_move}")
                continue
            energy_gain = move.get('energyGain')
            fast_move_turns = int(move.get('cooldown')/500)
            for charge_move in charge_moves:
                game_master_charge = moves.get(str(charge_move).lower())
                if not game_master_charge:
                    print(f"Missing {charge_move}")
                    continue
                energy = game_master_charge.get('energy')
                if energy_gain > 0:
                    counts[species_id][f'{fast_move.lower()} ({fast_move_turns}) [{energy_gain}] - {charge_move.lower()} [{energy}]'] = get_counts(energy, energy_gain, n_moves)
                else:
                    print(f"0 energy gain for {fast_move}")
    return counts


def get_counts(charge_move_energy, fast_move_energy, n_moves=5):
    """
    Returns the move counts given the fast move energy
    """
    counts = []
    total_energy = 0
    left_over_energy =  0
    for _ in range(n_moves):
        total_energy = left_over_energy
        count = 0
        while total_energy < charge_move_energy:
            total_energy += fast_move_energy
            count += 1
        left_over_energy = total_energy - charge_move_energy
        counts.append(count)
    return counts


def group_move_counts_by_fast_move(move_counts):
    """Group a Pokémon's move-count rows by their fast move for compact display."""
    grouped_counts = {}
    for pokemon, combinations in move_counts.items():
        grouped_counts[pokemon] = {}
        for combination, counts in combinations.items():
            fast_move, charge_move = combination.split(" - ", 1)
            grouped_counts[pokemon].setdefault(fast_move, []).append((charge_move, counts))
    return grouped_counts


def get_game_master():
    """
    Get game master data from db
    """
    global GAME_MASTER
    if GAME_MASTER:
        return GAME_MASTER
    
    engine = create_engine()
    query_results = engine.execute('SELECT * from `pokemon_data` WHERE pokemon_data.league="game_master";')
    results = [result for result in query_results]
    game_master = load_data(results[0][1])
    GAME_MASTER = game_master
    return game_master


def get_all_rankings(reset_data=False):
    """
    Get all rankings
    """
    # Skip the database queries if all rankings are already saved
    global ALL_RANKINGS
    if ALL_RANKINGS and not reset_data:
        return {
        pokemon['speciesId']: pokemon
        for pokemon in ALL_RANKINGS
    }

    # If no rankings saved yet then query the db once  
    engine = create_engine(timeout=120)
    all_rankings = []

    # make a single query for all leagues 
    sql_query = 'SELECT * from `pokemon_data`;'
    #result = engine.execute('SHOW GLOBAL VARIABLES LIKE "wait_timeout";')
    #print([x for x in result])
    query_results = engine.execute(sql_query)
    results = [result for result in query_results]
    for result in results:
        if not result[0].startswith('all_pokemon_'):
            continue
        all_rankings.extend(
            load_data(result[1])
        )
    ALL_RANKINGS = all_rankings
    return {
        pokemon['speciesId']: pokemon
        for pokemon in all_rankings
    }


def generate_move_strings(pokemon, pokemon_ranking, counts, chosen_fast_move=None, mega=None, popular_moves={}, chosen_charge_moves=[]):
    """
    Generate move strings for image
    """
    print(f"{pokemon}: {pokemon_ranking}")
    pokemon_moveset = {'fast': '', 'charge': []}
    # get three most common charge move
    num_moves = []
    num_fast_moves = []
    charged_moves = pokemon_ranking['moves']['chargedMoves']
    fast_moves = pokemon_ranking['moves']['fastMoves']
    print(charged_moves, fast_moves)
    print(popular_moves)

    if popular_moves:
        game_master = get_game_master()
        pokemon_in_gm_list = [p for p in game_master.get('pokemon', []) if p.get('speciesId', '') == pokemon]
        pokemon_in_gm = pokemon_in_gm_list[0] if pokemon_in_gm_list else {}

        charged_moves = [{'moveId': move_id.upper(), 'uses': num} for move_id, num in popular_moves.items() if move_id.upper() in pokemon_in_gm.get('chargedMoves')]
        fast_moves = [{'moveId': move_id.upper(), 'uses': num} for move_id, num in popular_moves.items() if move_id.upper() in pokemon_in_gm.get('fastMoves')]
    print(charged_moves, fast_moves)

    #sorted_moves = [move for move in pokemon_ranking['moves']['chargedMoves'] if move['uses']]
    sorted_moves = [move for move in charged_moves if move['uses'] is not None]

    # Pick the three moves at random if there are no use metrics
    if not sorted_moves:
        sorted_moves = pokemon_ranking['moves']['chargedMoves']
        for move in sorted_moves:
            move['uses'] = 0 # set uses to 0 so that all moves are even and chosen at random

    # Sort moves by number of uses in gobattlelog    
    ranked_moves = [move['moveId'] for move in sorted(sorted_moves, key=lambda x:x['uses'], reverse=True)]
    most_used_charges = ranked_moves[:3] if len(ranked_moves) >= 3 else ranked_moves
    
    # Pick the most used fast move
    unsorted_fast_moves = [move for move in fast_moves if move['uses'] is not None]
    most_used_fast_move = [move['moveId'] for move in sorted(unsorted_fast_moves, key=lambda x:x['uses'], reverse=True)][0]

    for move, count in counts.get(mega or pokemon, {}).items():
        # move looks like "fast_move (0) [1] - charge move [50]"
        fast_move = move.split('-')[0].split()[0]
        fast_move_turns = move.split('-')[0].split()[1]
        charge_move = move.split('-')[1].split()[0]

        # Check charge move
        print(f"*** move: {move} | count: {count}")
        if chosen_charge_moves:
            if charge_move.upper() not in chosen_charge_moves:
                continue
        elif charge_move.upper() not in most_used_charges: # Charge move not in most used
            #print(f"{pokemon} - charge {charge_move} not in most used")
            continue

        # Check fast move
        if chosen_fast_move:
            # if a fast move is chosen for the image
            if fast_move.upper() != chosen_fast_move.upper(): # Not a chosen fast move
                continue
            #if charge_move.upper() not in most_used_charges:
            #    continue
        elif most_used_fast_move.lower() != fast_move: # Fast move different than most used
            #print(f"{pokemon} - fast {fast_move} not the most used fast move")
            continue
        added = "-" if count[0] != count[1] else ""
        added = f"{added}*" if count[2] != count[0] else added
        #added = f"{added}^" if count[3] != count[0] else added
        #short_count = f"{count[0]}{'-' if count[0]!=count[1] else ''}"
        short_count = f"{count[0]}{added}"
        pokemon_moveset['fast'] = ' '.join(fast_move.upper().split('_')) + f" {fast_move_turns}"
        pokemon_moveset['charge'].append({'move': ' '.join(charge_move.upper().split("_")), 'count': short_count})
        #count_sequence = " · ".join(str(value) for value in count)
        #pokemon_moveset['fast'] = ' '.join(fast_move.upper().split('_')) + f" {fast_move_turns}"
        #pokemon_moveset['charge'].append({'move': ' '.join(charge_move.upper().split("_")), 'count': count_sequence})
    if not pokemon_moveset['charge']:
        pokemon_moveset['charge'] = [{'move': '???', 'count': '?'}, {'move': '???', 'count': '?'}]
    return pokemon_moveset





def make_image(pokemon_list, number_per_row=5, reset_data=False):
    """
    Make a move counts image from the list of pokemon
    """
    counts = get_move_counts(None)
    rankings = get_all_rankings(reset_data)
    pokemon_moves = get_popular_moves(days_back=30)
    image_url = "https://img.pokemondb.net/sprites/go/normal/{pokemon}.png"

    n_cards = len(pokemon_list) + 1  # +1 for the header/logo card
    n_rows = math.ceil(n_cards / number_per_row)
    image_width = MARGIN * 2 + number_per_row * CARD_W + (number_per_row - 1) * GAP
    image_height = MARGIN * 2 + HEADER_H + n_rows * CARD_H + (n_rows - 1) * GAP

    canvas = vertical_gradient((image_width, image_height), BG_TOP, BG_BOTTOM).convert("RGBA")
    title_tile = render_title_tile(
        image_width, HEADER_H, "POKÉMON GO MOVE COUNTS", "Fast move \u2192 charge move cycle reference"
    )
    canvas.alpha_composite(title_tile, (0, MARGIN))
    grid_top = MARGIN + HEADER_H

    row, col = -1, -1
    used_pokemon = []
    for pokemon in ["logo"] + sorted(pokemon_list):
        # extract pokemon from string if a fast move is chosen
        chosen_fast_move, chosen_charge_moves = None, []
        #z = re.match(r'(\w*)\((\w*)\)', pokemon)
        #if z:
        #    pokemon, chosen_fast_move = z.groups()
        z = re.match(r'(\w*)(\((.*)\))?(\[(.*)\])?', pokemon)
        if z:
            pokemon, _, chosen_fast_move, _, chosen_charge_moves_str = z.groups()
            if chosen_charge_moves_str:
                chosen_charge_moves = [move.upper() for move in chosen_charge_moves_str.split()][:3]
        #print(f"*** pokemon: {pokemon} - fast: {chosen_fast_move} - charge: {chosen_charge_moves}")
        
        # in case of mega/primal
        mega = ""
        z = re.findall(r"(.*)_(primal|mega)", pokemon)
        if z:
            print(f"Found primal or mega: {pokemon}.")
            mega = z[0]
            print(f"Found mega/primal {mega}")
        
        # Skip the pokemon if its not in the rankings
        pokemon_ranking = rankings.get(mega if mega else pokemon, {})
        if not pokemon_ranking and pokemon != "logo":
            print(f"Skipping {pokemon} because not in rankings")
            continue

        # Skip '?'
        if pokemon == '?':
            continue
        pokemon = pokemon.lower()

        # also skip shadow pokemon if it's counterpart is already in the list
        #  otherwise use the counterpart
        if pokemon.endswith('_shadow'):
            pokemon = pokemon[:-7]
            if pokemon in pokemon_list:
                continue
        
        pokemon_name = pokemon_ranking.get('speciesName')
        if pokemon_name:
            pokemon_name = pokemon_name.split()[0].lower()
        # add chosen fast move to used pokemon check
        used_pokemon_name = pokemon_name
        if chosen_fast_move:
            used_pokemon_name = f"{pokemon_name}({chosen_fast_move})"
        if chosen_charge_moves_str:
            used_pokemon_name = f"{used_pokemon_name}_{chosen_charge_moves_str}"
        if used_pokemon_name in used_pokemon:
            print(f"Skipping {pokemon} because already in the image")
            continue
        url = image_url.format(pokemon=pokemon.replace("_", "-"))
        col += 1
        if col % number_per_row == 0:
            row += 1
            col = 0
        print(f"row: {row}, col: {col}")

        if not os.path.exists("pokemon_images"):
            os.mkdir("pokemon_images")

        pokemon_image = f"pokemon_images/{pokemon}.png" if pokemon != "logo" else "static/newFlippinCoopLogo.png"
        img2 = None

        print(f"Downloading image for {pokemon} ({pokemon_name})")
        img_path = download_pokemon_image(pokemon, pokemon_name)
        '''
        if not os.path.exists(pokemon_image):
            img_data = requests.get(url).content
            with open(f"pokemon_images/{pokemon}.png", 'wb') as handler:
                handler.write(img_data)
        '''

        def alt_name(pokemon, pokemon_name, img_path=None):
            if img_path:
                try:
                    img2 = Image.open(img_path)
                    return img_path
                except:
                    pass
            pokemon_image = f"pokemon_images/{pokemon}.png" if pokemon != "logo" else "static/newFlippinCoopLogo.png"
            try:
                print(f"trying {pokemon_image}")
                img2 = Image.open(pokemon_image)
                return pokemon_image
            except:
                pokemon_image = f"pokemon_images/{pokemon_name}.png" if pokemon != "logo" else "static/newFlippinCoopLogo.png"
                print(f"using {pokemon_image}")
                return pokemon_image


        # Load sprite image
        sprite_img = None
        try:
            pokemon_image = alt_name(pokemon, pokemon_name, img_path=img_path)
            sprite_img = Image.open(pokemon_image)
        except Exception as error:
            print(f"Cannot add image for {pokemon} because:  {error}")

        card_x = MARGIN + col * (CARD_W + GAP)
        card_y = grid_top + row * (CARD_H + GAP)

        # Draw the branded header/legend card in place of the old "logo" cell
        if pokemon == "logo":
            tile = render_card_tile(draw_header_card, sprite_img, HELP_LINES)
            canvas.alpha_composite(tile, (card_x - CARD_PAD, card_y - CARD_PAD))
            continue

        # add move count text for pokemon
        popular_moves = pokemon_moves.get(pokemon, {})
        pokemon_moveset = generate_move_strings(
            pokemon, pokemon_ranking, counts,
            chosen_fast_move=chosen_fast_move, mega=mega, popular_moves=popular_moves,
            chosen_charge_moves=chosen_charge_moves
        )
        tile = render_card_tile(draw_move_card, pokemon, pokemon_moveset, sprite_img)
        canvas.alpha_composite(tile, (card_x - CARD_PAD, card_y - CARD_PAD))
        used_pokemon.append(used_pokemon_name)

    canvas.convert("RGB").save("image.png")




def download_pokemon_image(pokemon, pokemon_name=None, used_pokemon_name=False):
    pokemon_image = f"static/images/pokemon_images/{pokemon}.png" if pokemon != "logo" else "static/newFlippinCoopLogo.png"
    image_url = "https://img.pokemondb.net/sprites/go/normal/{pokemon}.png"
    url = image_url.format(pokemon=pokemon.replace("_", "-"))

    if not os.path.exists(pokemon_image):
        print(f"Downloading image for {pokemon} at: {url}")
        resp = requests.get(url)
        if resp.status_code in [304, 404]:
            print(f"Missing image for {pokemon}. Altername name: {pokemon_name}")
            if not used_pokemon_name and pokemon_name:
                # try with the pokemon's name
                print(f"checking alertnate pokemon name for image: {pokemon_name}")
                return download_pokemon_image(pokemon_name, used_pokemon_name=False)
            return
        img_data = resp.content
        with open(pokemon_image, 'wb') as handler:
            handler.write(img_data)
        
        # make img have transparent background
        img = Image.open(pokemon_image)
        img.convert("RGBA")
        datas = img.getdata()
        newData = []

        for item in datas:
            if item[0] == 255 and item[1] == 255 and item[2] == 255:
                newData.append((255,255,255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        img.save(pokemon_image)
    return pokemon_image




if __name__ == '__main__':
    pokemon_list = ["bulbasaur", "venusaur", "charizard", "rapidash", "raichu", "walrein", "magnezone", "swampert", "pikachu"]
    pokemon_list = [
        "abomasnow", "articuno(ice_shard)", "blastoise", "charizard", "clefable", "cresselia",
        "drapion", "drifblim", "escavalier", "ferrothorn", "giratina", "gligar",
        "gyarados", "jellicent", "lapras(water_gun)", "lugia", "machamp", "magnezone", "mandibuzz",
        "meganium", "muk", "nidoqueen", "ninetales", "ninetales_alolan", "pidgeot", "politoed",
        "poliwrath", "regice", "regirock", "registeel", "scrafty", "skarmory", "snorlax",
        "steelix", "swampert", "sylveon", "talonflame(fire_spin)", "talonflame", "toxicroak", "trevenant",
        "umbreon", "venusaur", "walrein", "zapdos", "obstagoon",
        "miltank", "dubwool"
    ]
    make_image(pokemon_list)
