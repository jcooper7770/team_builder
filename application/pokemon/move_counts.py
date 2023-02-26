"""
Move counts table for all pokemon

TODO:
 - [DONE] pick only meta relevant pokemon
 - [DONE] pick only meta relevant moves

  $ python -m application.pokemon.move_counts
"""

from dataclasses import dataclass
import json
import os.path
import logging
import re
import requests

from PIL import Image, ImageDraw, ImageFont

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

ALL_RANKINGS = []
GAME_MASTER = {}

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
        if chosen_pokemon and chosen_pokemon not in species_id:
            continue
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
                game_master_charge = moves.get(charge_move.lower())
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
    game_master = json.loads(json.loads(results[0][1]))
    GAME_MASTER = game_master
    return game_master


def get_all_rankings():
    """
    Get all rankings
    """
    # Skip the database queries if all rankings are already saved
    global ALL_RANKINGS
    if ALL_RANKINGS:
        return {
        pokemon['speciesId']: pokemon
        for pokemon in ALL_RANKINGS
    }

    # If no rankings saved yet then query the db once  
    engine = create_engine()
    all_rankings = []

    # make a single query for all leagues 
    sql_query = 'SELECT * from `pokemon_data`;'
    query_results = engine.execute(sql_query)
    results = [result for result in query_results]
    for result in results:
        if not result[0].startswith('all_pokemon_'):
            continue
        all_rankings.extend(json.loads(json.loads(result[1])))
    ALL_RANKINGS = all_rankings
    return {
        pokemon['speciesId']: pokemon
        for pokemon in all_rankings
    }


def generate_move_strings(pokemon, pokemon_ranking, counts, chosen_fast_move=None, mega=None):
    """
    Generate move strings for image
    """
    pokemon_moveset = {'fast': '', 'charge': []}
    # get three most common charge move
    sorted_moves = [move for move in pokemon_ranking['moves']['chargedMoves'] if move['uses']]

    # Pick the three moves at random if there are no use metrics
    if not sorted_moves:
        sorted_moves = pokemon_ranking['moves']['chargedMoves']
        for move in sorted_moves:
            move['uses'] = 0 # set uses to 0 so that all moves are even and chosen at random

    # Sort moves by number of uses in gobattlelog    
    ranked_moves = [move['moveId'] for move in sorted(sorted_moves, key=lambda x:x['uses'], reverse=True)]
    most_used_charges = ranked_moves[:3] if len(ranked_moves) >= 3 else ranked_moves

    for move, count in counts.get(mega or pokemon, {}).items():
        # move looks like "fast_move (0) [1] - charge move [50]"
        fast_move = move.split('-')[0].split()[0]
        charge_move = move.split('-')[1].split()[0]

        if chosen_fast_move:
            # if a fast move is chosen for the image
            if fast_move.upper() != chosen_fast_move.upper():
                continue
            if charge_move.upper() not in most_used_charges:
                continue
        elif pokemon_ranking and pokemon_ranking.get('moveset', []):
            # if the fast move is not as recommended
            if not pokemon_ranking.get('moveset')[0].lower() == fast_move:
                continue
            # if the charge move is not as recommended
            if not charge_move.upper() in most_used_charges:
                continue
        added = "-" if count[0] != count[1] else ""
        added = f"{added}*" if count[2] != count[0] else added
        #added = f"{added}^" if count[3] != count[0] else added
        #short_count = f"{count[0]}{'-' if count[0]!=count[1] else ''}"
        short_count = f"{count[0]}{added}"
        pokemon_moveset['fast'] = ' '.join(fast_move.upper().split('_'))
        pokemon_moveset['charge'].append({'move': ' '.join(charge_move.upper().split("_")), 'count': short_count})

    if not pokemon_moveset['charge']:
        pokemon_moveset['charge'] = [{'move': '???', 'count': '?'}, {'move': '???', 'count': '?'}]

    return pokemon_moveset


def add_counts_to_img(pokemon, pokemon_moveset, blank_img, row, col, fonts):
    """
    Adds the move counts text to the image
    """
    image_font, cm_image_font, count_image_font = fonts
    imgText = ImageDraw.Draw(blank_img)
    charge_xpos = (2*col + 1)*100 + 32

    # Draw fast move
    draw_text(
        imgText,
        (charge_xpos, row*100 + 10),
        pokemon_moveset['fast'],
        font=image_font
    )
    print(pokemon, pokemon_moveset)

    # Draw charge moves
    draw_text(
        imgText,
        (charge_xpos, row*100 + 20),
        pokemon_moveset['charge'][0]['move'],
        font=cm_image_font
    )
    draw_text(
        imgText,
        (charge_xpos, row*100 + 45),
        pokemon_moveset['charge'][0]['count'],
        font=count_image_font
    )

    # second charge move
    draw_text(
        imgText,
        (charge_xpos + 33 if len(pokemon_moveset['charge'])==3 else charge_xpos, row*100 + 60),
        pokemon_moveset['charge'][1]['move'],
        font=cm_image_font
    )
    draw_text(
        imgText,
        (charge_xpos + 33 if len(pokemon_moveset['charge'])==3 else charge_xpos, row*100 + 85),
        pokemon_moveset['charge'][1]['count'],
        font=count_image_font
    )
    
    if len(pokemon_moveset['charge']) == 3:
        draw_text(
            imgText,
            (charge_xpos - 33, row*100 + 95),
            pokemon_moveset['charge'][2]['move'],
            font=cm_image_font,
        )
        draw_text(
            imgText,
            (charge_xpos - 33, row*100 + 85),
            pokemon_moveset['charge'][2]['count'],
            font=count_image_font,
        )


def make_image(pokemon_list, number_per_row=5):
    """
    Make a move counts image from the list of pokemon
    """
    counts = get_move_counts(None)
    rankings = get_all_rankings()
    image_url = "https://img.pokemondb.net/sprites/go/normal/{pokemon}.png"
    image_height = ((len(pokemon_list) + 1) // number_per_row) * 100 + 100
    image_width = number_per_row * 200
    blank_img = Image.new("RGB", (image_width, image_height), (219, 226, 233))
    image_font = ImageFont.truetype("static/arialbd.ttf", 11)
    cm_image_font = ImageFont.truetype("static/arialbd.ttf", 8)
    count_image_font = ImageFont.truetype("static/arialbd.ttf", 27)
    row, col = -1, -1
    for pokemon in ["logo"] + sorted(pokemon_list):
        # extract pokemon from string if a fast move is chosen
        chosen_fast_move = None
        z = re.match(r'(\w*)\((\w*)\)', pokemon)
        if z:
            pokemon, chosen_fast_move = z.groups()
        
        # in case of mega/primal
        mega = ""
        z = re.findall(r"(.*)_[primal|mega]", pokemon)
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

        # Download image
        if not os.path.exists(pokemon_image):
            img_data = requests.get(url).content
            with open(f"pokemon_images/{pokemon}.png", 'wb') as handler:
                handler.write(img_data)

        # Paste image in canvas
        try:
            img2 = Image.open(pokemon_image)
            img2copy = img2.copy()
            img2copy = img2copy.resize((100, 100))
            blank_img.paste(img2copy, (2*col*100, row*100), img2copy.convert("RGBA"))
        except Exception as error:
            print(f"Cannot add image for {pokemon} because:  {error}")
        
        if pokemon != "logo":
            pokemonText = ImageDraw.Draw(blank_img)
            draw_text(
                pokemonText,
                (2*col*100, row*100+10),
                pokemon,
                font=image_font,
                anchor="ls"
            )

        rectangle = ImageDraw.Draw(blank_img)
        rectangle.rectangle(
            [(2*col)*100, row*100, (2*col+1)*100 + 100, row*100 + 100],
            outline="black"
        )

        # Skip move text for the logo
        if pokemon == "logo":
            imgText = ImageDraw.Draw(blank_img)
            charge_xpos = (2*col + 1)*100 + 50
            draw_text(
                imgText,
                (charge_xpos, row*100 + 10),
                HELP_TEXT,
                font=cm_image_font
            )
            continue

        # add move count text for pokemon
        pokemon_moveset = generate_move_strings(pokemon, pokemon_ranking, counts, chosen_fast_move=chosen_fast_move, mega=mega)
        add_counts_to_img(pokemon, pokemon_moveset, blank_img, row, col, [image_font, cm_image_font, count_image_font])

    blank_img.save("image.png")


def draw_text(imgText, position, text, font, anchor="ms"):
    """
    Draws text with gray background
    """
    bbox = imgText.textbbox(
        position,
        f" {text} ",
        font=font,
        anchor=anchor
    )
    new_size = (0, -2, 0, 2)
    new_bbox = tuple(sum(x) for x in zip(bbox, new_size))
    #imgText.rectangle(bbox, fill=(128, 128, 128, 25)) # grey background to text
    #imgText.rectangle(bbox, fill=(255,255,255, 25), outline="#000000") # white background with black outline
    imgText.rectangle(new_bbox, fill=(255,255,255, 25), outline="#000000")
    imgText.text(
        position,
        text,
        font=font,
        fill=(0, 0, 0),
        anchor=anchor
    )

if __name__ == '__main__':
    pokemon_list = ["bulbasaur", "venusaur", "charizard", "rapidash", "raichu", "walrein", "magnezone", "swampert", "pikachu"]
    pokemon_list = [
        "abomasnow", "articuno(ice_shard)", "blastoise", "charizard", "clefable", "cresselia",
        "drapion", "drifblim", "escavalier", "ferrothorn", "giratina", "gligar",
        "gyarados", "jellicent", "lapras(water_gun)", "lugia", "machamp", "magnezone", "mandibuzz",
        "meganium", "muk", "nidoqueen", "ninetales", "pidgeot", "politoed",
        "poliwrath", "regice", "regirock", "registeel", "scrafty", "skarmory", "snorlax",
        "steelix", "swampert", "sylveon", "talonflame(fire_spin)", "talonflame", "toxicroak", "trevenant",
        "umbreon", "venusaur", "walrein", "zapdos", "obstagoon",
        "miltank", "dubwool"
    ]
    make_image(pokemon_list)
