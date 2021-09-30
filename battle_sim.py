'''

  TODO:
    - [DONE] Determine pokemon level and ideal IVs from league
'''
import math


class Move:
    """ A single move """
    def __init__(self, damage, energy, turns):
        self.damage = damage
        self.energy = energy # energyGain|energyCost
        self.turns = turns

class Moves:
    """ Pokmeon moves """
    def __init__(self, fast, charge1, charge2):
        self.fast = fast
        self.charge1 = charge1
        self.charge2 = charge2

class Pokemon:
    def __init__(self, pid, health, fast_move, charge_move, shields):
        self.id = pid
        self.energy = 0
        self.health = health
        self.fast_move = fast_move
        self.charge_move = charge_move
        self.shields = shields

    def damage(self, amount):
        self.health -= amount

    def attack(self):
        """ fast move """
        self.energy += self.fast_move['energyGain']
        if self.energy > 100:
            self.energy = 100

    def check_charge(self):
        """ Throws the charge move if enough energy """        
        return self.energy >= self.charge_move['energy']

    def take_charge(self, damage):
        """ Take charge move from other pokemon """
        if self.shields == 0:
            self.damage(damage)
        else:
            print(f"{self} used a shield")
            self.shields -= 1
            self.damage(1)

    def __str__(self):
        return f"{self.id} ({self.health}, {self.energy})"

    def __repr__(self):
        return self.__str__()


def calculate_cpm_list():
    """
    Creates a list of CP Multipliers
    note: list is incorrect. Almost right though
    cpm(level+1/2) = sqrt( 1/2 * (cpm(level)^2 + cpm(level+1)^2) )
    Tried to extrapolte to get cpm(level+1) from cpm(level) and cpm(level+1/2)
    but didn't give right values
    """
    start1 = 0.094
    start2 = 0.135137432
    cpm_dict = {'1': start1, '1.5': start2}
    cpms = [start1, start2]
    level = 2
    for _ in range(100):
        next_cpm = math.sqrt((start2 ** 2) * 2 - (start1 ** 2))
        start1 = start2
        start2 = next_cpm
        cpms.append(next_cpm)
        cpm_dict[str(level)] = next_cpm
        level += 0.5
    return cpms, cpm_dict
    

def get_pokemon_from_master(master, pokemon_list):
    """
    Returns the pokemon from the game master
    {species1Id: pokemon1, species2Id: pokemon2, ...}
    """
    return_pokemon = {}
    for p in master.get('pokemon'):
        for pokemon in pokemon_list:
            if p.get('speciesId') == pokemon:
                return_pokemon[pokemon] = p
    return return_pokemon


def get_moves_from_master(master, moves):
    """
    Returns the moves from the game master
    {move1Id: move1, move2Id: move2 ...}
    """
    return_moves = {}
    for m in master.get('moves'):
        for move in moves:
            if m.get('moveId') == move:
                return_moves[move] = m
    return return_moves


def calculate_move_damage(move, attacker, defender, team_creator):
    """
    Returns the amount of damage a move does from the attacker to the defender
    """
    attacker_level = attacker['level']
    defender_level = defender['level']
    attacker_cpm = team_creator.cp_multipliers[attacker_level]
    defender_cpm = team_creator.cp_multipliers[defender_level]
    power = float(move.get('power'))
    attack = float(attacker.get('baseStats').get('atk') + attacker['ivs'][0]) * attacker_cpm
    defense = float(defender.get('baseStats').get('def') + defender['ivs'][1]) * defender_cpm
    stab = 1.2 if move.get('type') in attacker.get('types') else 1.0
    effectiveness = float(team_creator.get_effectiveness(move.get('type'), defender.get('types')))

    # PVPoke uses a bonus multiplier value. Not sure why..
    # https://github.com/pvpoke/pvpoke/blob/master/src/js/battle/Battle.js#L221
    bonus_multiplier = 1.3
    print(f"{move.get('moveId')} effectiveness: {effectiveness}")
    print(f"p: {power} - a: {attack} - d: {defense} - s: {stab} - e: {effectiveness}")
    return math.floor(0.5 * power * attack / defense * stab * effectiveness * bonus_multiplier) + 1


def sim_battle(pokemon1, pokemon2, team_creator):
    """
    Simulate a battle between two pokemon
    """
    movesets = team_creator.team_maker.species_moveset_dict
    game_master = team_creator.team_maker.game_master

    # Get data on each pokemon
    pokemon = get_pokemon_from_master(game_master, [pokemon1, pokemon2])
    pokemon1_data = pokemon[pokemon1]
    pokemon2_data = pokemon[pokemon2]
    pokemon1_data['moveset'] = movesets[pokemon1]
    pokemon2_data['moveset'] = movesets[pokemon2]

    print(pokemon1_data)
    print(pokemon2_data)

    # Get pokemon IVs
    league_cp = team_creator.team_maker.league_cp
    pokemon1_ivs = pokemon1_data['defaultIVs'].get(f'cp{league_cp}', [40, 15, 15, 15])
    pokemon2_ivs = pokemon2_data['defaultIVs'].get(f'cp{league_cp}', [40, 15, 15, 15])
    print(pokemon1_ivs)
    print(pokemon2_ivs)
    pokemon1_data['level'] = pokemon1_ivs[0]
    pokemon1_data['ivs'] = pokemon1_ivs[1:]

    pokemon2_data['level'] = pokemon2_ivs[0]
    pokemon2_data['ivs'] = pokemon2_ivs[1:]

    # Get how much damage the moves do
    # Damage from pokemon1->2
    move1_damage = {}
    pokemon1_moves = get_moves_from_master(game_master, pokemon1_data['moveset'])
    print(pokemon1_moves)
    for move in pokemon1_moves.values():
        move1_damage[move.get('moveId')] = calculate_move_damage(move, pokemon1_data, pokemon2_data, team_creator)
    print(move1_damage)
        

    # Damage from pokemon2->2
    move2_damage = {}
    pokemon2_moves = get_moves_from_master(game_master, pokemon2_data['moveset'])
    print(pokemon2_moves)
    for move in pokemon2_moves.values():
        move2_damage[move.get('moveId')] = calculate_move_damage(move, pokemon2_data, pokemon1_data, team_creator)
    print(move2_damage)

    # Make them battle

    # calculate number of pokemon1 fast moves to charge moves
    p1_fastmove = pokemon1_moves[movesets[pokemon1][0]]
    p1_fastmove['damage'] = move1_damage[p1_fastmove['moveId']]
    p1_chargemove1 = pokemon1_moves[movesets[pokemon1][1]]
    p1_chargemove1['damage'] = move1_damage[p1_chargemove1['moveId']]
    p1_chargemove2 = pokemon1_moves[movesets[pokemon1][2]]
    p1_count1 = p1_chargemove1['energy'] / p1_fastmove['energyGain']
    p1_count2 = p1_chargemove2['energy'] / p1_fastmove['energyGain']
    print(f"pokemon1 counts: {p1_count1} {p1_count2}")

    # calculate number of pokemon2 fast moves to charge moves
    p2_fastmove = pokemon2_moves[movesets[pokemon2][0]]
    p2_fastmove['damage'] = move2_damage[p2_fastmove['moveId']]
    p2_chargemove1 = pokemon2_moves[movesets[pokemon2][1]]
    p2_chargemove1['damage'] = move2_damage[p2_chargemove1['moveId']]
    p2_chargemove2 = pokemon2_moves[movesets[pokemon2][2]]
    p2_count1 = p2_chargemove1['energy'] / p2_fastmove['energyGain']
    p2_count2 = p2_chargemove2['energy'] / p2_fastmove['energyGain']
    print(f"pokemon2 counts: {p2_count1} {p2_count2}")

    p1_health = math.floor((pokemon1_data['baseStats']['hp']+pokemon1_data['ivs'][2])*team_creator.cp_multipliers[pokemon1_data['level']])
    p2_health = math.floor((pokemon2_data['baseStats']['hp']+pokemon2_data['ivs'][2])*team_creator.cp_multipliers[pokemon2_data['level']])
    print(f"p1 health: {p1_health} - p2 health: {p2_health}")
    healths = {pokemon1: p1_health, pokemon2: p2_health}

    # THE BATTLE
    p1_energy, p2_energy = (0, 0)
    move_seconds = (p1_fastmove['cooldown'], p2_fastmove['cooldown'])
    shields = [1, 1]
    turns = 0
    pokemons = [
        Pokemon(pokemon1, p1_health, p1_fastmove, p1_chargemove1, shields[0]),
        Pokemon(pokemon2, p2_health, p2_fastmove, p2_chargemove1, shields[1])
    ]

    while pokemons[0].health > 0 and pokemons[1].health > 0:
        turns += 1
        print(f"{pokemons[0]}\t{pokemons[1]}")
        for num, pokemon in enumerate(pokemons):
            # determine if fast move is done
            if turns * 500 % pokemon.fast_move['cooldown'] == 0:
                # keep track of other pokemon health
                pokemons[1-num%2].damage(pokemon.fast_move['damage'])

                # Keep track of energy
                pokemon.attack()

                # throw charge move
                if pokemon.check_charge():
                    print(f"{pokemon} threw {pokemon.charge_move['moveId']}")
                    pokemon.energy -= pokemon.charge_move['energy']
                    pokemons[1-num%2].take_charge(pokemon.charge_move['damage'])

    print(f"{pokemons[0]}\t{pokemons[1]}")

    winner = pokemon1
    if pokemons[0].health <= 0:
        winner = pokemon2
        leftover_health =  float(pokemons[1].health)/ healths[pokemon2]
    else:
        leftover_health =  float(pokemons[0].health) / healths[pokemon1]
    print(f"{winner} won with {leftover_health*100:.2f}% health remaining!")
    
    return winner, leftover_health
    

if __name__ == '__main__':
    from team_building import MetaTeamDestroyer, TeamCreater
    print("Initializing data...")
    team_creator = MetaTeamDestroyer(league="Jungle")
    tc = TeamCreater(team_creator)

    print("Simulating battle")
    #sim_battle('stunfisk_galarian', 'venusaur', tc)
    #results = sim_battle('stunfisk_galarian', 'scrafty', tc)
    results = sim_battle('scrafty', 'stunfisk_galarian', tc)
    print(results)
    #sim_battle('stunfisk_galarian', 'dialga', tc)
    #sim_battle('talonflame', 'dialga', tc)
