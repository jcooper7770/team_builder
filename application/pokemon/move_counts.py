"""
Move counts table for all pokemon

TODO:
 - pick only meta relevant pokemon
 - pick only meta relevant moves
"""

from dataclasses import dataclass
import json
import os.path

import sqlalchemy
from PIL import Image, ImageDraw, ImageFont

from application.utils.database import create_engine
#from ..utils.database import create_engine


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
    print(moves)
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
            if "HIDDEN_POWER" in fast_move:
                continue
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


def get_counts(energy, energy_gain, n_moves=5):
    """
    Returns the move counts given the energy gain
    """
    # first N moves
    counts = []
    total_energy = energy * n_moves
    energy_remaining = 0
    for _ in range(n_moves):
        count = (energy - energy_remaining) // energy_gain
        if energy % energy_gain:
            count = count + 1
        counts.append(count)

        total_energy = (energy_gain * count) + energy_remaining
        energy_remaining = total_energy - energy
    return counts


def get_game_master():
    """
    Get game master data from db
    """
    engine = create_engine()
    query_results = engine.execute('SELECT * from `pokemon_data` WHERE pokemon_data.league="game_master";')
    results = [result for result in query_results]
    game_master = json.loads(json.loads(results[0][1]))
    #print(game_master)
    #print(type(game_master))
    return game_master


def get_gl_rankings():
    """
    Get GL rankings
    """
    engine = create_engine()
    query_results = engine.execute('SELECT * from `pokemon_data` WHERE pokemon_data.league="all_pokemon_GL";')
    query_results2 = engine.execute('SELECT * from `pokemon_data` WHERE pokemon_data.league="all_pokemon_UL";')
    results = [result for result in query_results]
    results2 = [result for result in query_results2]
    rankings = json.loads(json.loads(results[0][1])) + json.loads(json.loads(results2[0][1]))
    return {
        pokemon['speciesId']: pokemon
        for pokemon in rankings
    }


def make_image(pokemon_list, number_per_row=5):
    """
    Make a move counts image from the list of pokemon
    """
    import requests
    counts = get_move_counts(None)
    rankings = get_gl_rankings()
    print(rankings)
    #image_url = "https://img.pokemondb.net/sprites/black-white/normal/{pokemon}.png"
    image_url = "https://img.pokemondb.net/sprites/home/normal/{pokemon}.png"
    image_url = "https://img.pokemondb.net/sprites/go/normal/{pokemon}.png"
    blank_img = Image.new("RGB", (1000, 1000), (255, 255, 255))
    image_font = ImageFont.truetype("static/arialbd.ttf", 11)
    cm_image_font = ImageFont.truetype("static/arialbd.ttf", 8)
    count_image_font = ImageFont.truetype("static/arialbd.ttf", 27)
    for poke_num, pokemon in enumerate(["logo"] + sorted(pokemon_list)):
        pokemon = pokemon.lower()
        url = image_url.format(pokemon=pokemon.replace("_", "-"))
        row = poke_num // number_per_row
        col = poke_num - row * number_per_row
        print(f"row: {row}, col: {col}")

        if not os.path.exists("pokemon_images"):
            os.mkdir("pokemon_images")

        pokemon_image = f"pokemon_images/{pokemon}.png" if pokemon != "logo" else "static/flippinCoopLogo.png"
        img2 = None

        # Download image
        if not os.path.exists(pokemon_image):
            img_data = requests.get(url).content
            with open(f"pokemon_images/{pokemon}.png", 'wb') as handler:
                handler.write(img_data)

            '''
            # change images to have white background
            img2 = Image.open(pokemon_image)
            img2copy = img2.copy()
            pokemon_colored = img2copy.convert("RGBA")
            pix_data = pokemon_colored.load()
            for y in range(pokemon_colored.size[1]):
                for x in range(pokemon_colored.size[0]):
                    if pix_data[x, y] == (0, 0, 0, 255):
                        pokemon_colored.putpixel((x, y), (255, 255, 255, 255))
            pokemon_colored.save(pokemon_image)
            '''
        
        # Paste image in canvas
        try:
            img2 = Image.open(pokemon_image)
            img2copy = img2.copy()
            img2copy = img2copy.resize((100, 100))
            blank_img.paste(img2copy, (2*col*100, row*100), img2copy.convert("RGBA"))
        except Exception as error:
            print(f"Cannot add image for {pokemon} because:  {error}")

        rectangle = ImageDraw.Draw(blank_img)
        rectangle.rectangle(
            [(2*col)*100, row*100, (2*col+1)*100 + 100, row*100 + 100],
            outline="black"
        )

        # Skip move text for the logo
        if pokemon == "logo":
            continue

        # add move count text for pokemon
        move_text = ""
        moves = []
        pokemon_ranking = rankings.get(pokemon, {})
        pokemon_moveset = {'fast': '', 'charge': []}
        for move, count in counts.get(pokemon, {}).items():
            fast_move = move.split('-')[0].split()[0]
            charge_move = move.split('-')[1].split()[0]
            if pokemon_ranking and pokemon_ranking.get('moveset', []):
                if not pokemon_ranking.get('moveset')[0].lower() == fast_move:
                    continue
                if not charge_move in [move.lower() for move in pokemon_ranking.get('moveset')][1:]:
                    continue
            short_fast_move = ''.join(f"{word[0].upper()}{word[1].lower()}" for word in fast_move.split("_"))
            short_charge = ''.join(f"{word[0].upper()}{word[1].lower()}" if len(word)>1 else f"{word[0].upper}" for word in charge_move.split('_'))
            short_count = f"{count[0]}{'-' if count[0]!=count[1] else ''}"
            moves.append(f"{short_fast_move} - {short_charge}: {short_count}")

            pokemon_moveset['fast'] = ' '.join(fast_move.upper().split('_'))
            pokemon_moveset['charge'].append({'move': ' '.join(charge_move.upper().split("_")), 'count': short_count})
        move_text = "\n".join(moves)

        #move_text = "\n".join(f"{move}:\n   {counts}" for move, counts in counts.get(pokemon, {}).items())
        imgText = ImageDraw.Draw(blank_img)
        '''
        imgText.text(
            ((2*col + 1)*100, row*100 + 30),
            move_text,
            fill=(100,0,0),
            font=image_font
        )
        '''

        imgText.text(
            ((2*col + 1)*100 +50, row*100 + 10),
            pokemon_moveset['fast'],
            fill=(100,0,0),
            font=image_font,
            anchor="ms"
        )
        imgText.text(
            ((2*col + 1)*100 + 50, row*100 + 20),
            pokemon_moveset['charge'][0]['move'],
            fill=(100,0,0),
            font=cm_image_font,
            anchor="ms"
        )
        imgText.text(
            ((2*col + 1)*100 + 50, row*100 + 45),
            pokemon_moveset['charge'][0]['count'],
            fill=(100,0,0),
            font=count_image_font,
            anchor="ms"
        )
        imgText.text(
            ((2*col + 1)*100 + 50, row*100 + 65),
            pokemon_moveset['charge'][1]['move'],
            fill=(100,0,0),
            font=cm_image_font,
            anchor="ms"
        )
        imgText.text(
            ((2*col + 1)*100 + 50, row*100 + 90),
            pokemon_moveset['charge'][1]['count'],
            fill=(100,0,0),
            font=count_image_font,
            anchor="ms"
        )




    blank_img.save("image.png")

if __name__ == '__main__':
    pokemon_list = ["bulbasaur", "venusaur", "charizard", "rapidash", "raichu", "walrein", "magnezone", "swampert", "pikachu"]
    pokemon_list = [
        "abomasnow", "articuno", "blastoise", "charizard", "clefable", "cresselia",
        "drapion", "drifblim", "escavalier", "ferrothorn", "giratina", "gligar",
        "gyarados", "jellicent", "lapras", "lugia", "machamp", "magnezone", "mandibuzz",
        "meganium", "muk", "nidoqueen", "ninetales", "pidgeot", "politoed",
        "poliwrath", "regice", "regirock", "registeel", "scrafty", "skarmory", "snorlax",
        "steelix", "swampert", "sylveon", "talonflame", "toxicroak", "trevenant",
        "umbreon", "venusaur", "walrein", "zapdos", "obstagoon",
        "miltank", "dubwool"
    ]
    make_image(pokemon_list)
