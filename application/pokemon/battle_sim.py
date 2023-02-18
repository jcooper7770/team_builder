'''
Simulate battles between two pokemon

  TODO:
    - [DONE] Determine pokemon level and ideal IVs from league
    - Figure out proper charge move to throw instead of the first one
    - [DONE] Add buff/debuff
    - [DONE] Implement fast move sneaks
    - Wait entire fast move time until the opponent can throw it's charge move
        that way the damage and energy goes through before/after a charge move is thrown
'''

import math
import threading
import time
import random
import re


# from https://9db.jp/pokego/data/50
STATUS_EFFECT = {
    "att": [1.25, 1.5, 1.75, 2.0], # 5/4, 6/4, 7/4, 8/4
    "def": [0.8, 0.667, 0.5714286, 0.5] # 4/5, 4/6, 4/7, 4/8
}
ALWAYS_BUFF = False


class Move:
    """ A single move """
    def __init__(self, damage, energy, turns):
        self.damage = damage
        self.energy = energy # energyGain|energyCost
        self.turns = turns

class Moveset:
    """ Pokmeon moveset """
    def __init__(self, fast, charge1, charge2):
        self.fast = fast
        self.charge1 = charge1
        self.charge2 = charge2

    def energy_efficient(self):
        """ Returns the more energy efficient charge move """
        return sorted([self.charge1, self.charge2], key=lambda x: x['damage']/x['energy'], reverse=True)[0]

    def higher_damage(self):
        """ Returns the charge move with the higher damage """
        if self.charge1['damage'] == self.charge2['damage']:
            return self.energy_efficient()
        return self.charge1 if self.charge1['damage'] > self.charge2['damage'] else self.charge2

    def bait_move(self):
        """ Returns the bait move (as the less energy move) """
        return sorted([self.charge1, self.charge2], key=lambda x: x['energy'])[0]


class Pokemon:
    def __init__(self, pid, health, shields, data, moveset):
        self.id = pid
        self.energy = 0
        self.health = health
        self.shields = shields
        self.data = data
        self.charge_moves_thrown = 0
        self.moveset = moveset
        self.turns = 0 # To help keep track of sneaking moves
        self.fastmove_turns = moveset.fast['cooldown'] / 500
        self.fastmoves_thrown = 0
        self.charge_thrown = False
        self.is_attacking = False
        self.turns = 0
        self.att_status = 0
        self.def_status = 0
        
    def damage(self, amount):
        self.health -= amount
        if self.health < 0:
            self.health = 0

    def attack(self):
        """ fast move """
        self.energy += self.moveset.fast['energyGain']
        if self.energy > 100:
            self.energy = 100
        self.turns += self.moveset.fast['cooldown'] / 500
        self.fastmoves_thrown += 1

    def check_charge(self, opponent_shields=1, opponent_damage=10):
        """ Throws the charge move if enough energy """
        higher_damage_move = self.moveset.higher_damage()
        if self.energy >= higher_damage_move['energy']:
            # Bait the less energy move on first charge move
            self.charge_thrown = True
            if self.charge_moves_thrown == 0 and opponent_shields > 0:
                return self.moveset.bait_move()
            return higher_damage_move
        elif self.health <= opponent_damage: # if low health then throw smaller move
            bait_move = self.moveset.bait_move()
            if self.energy >= bait_move['energy']:
                self.charge_thrown = True
                return self.moveset.bait_move()
        return None
        #return self.energy >= self.charge_move['energy']

    def take_charge(self, damage):
        """ Take charge move from other pokemon """
        if self.shields == 0:
            self.damage(damage)
            return True

        # Used a shield so takes shield damage
        self.shields -= 1
        self.damage(1)
        return False

    def __str__(self):
        return f"{self.id} ({self.health}, {self.energy}, {self.fastmoves_thrown})"

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


def get_pokemon_stat(pokemon, team_creator, stat):
    """
    Returns the attack stat
    """
    
    pokemon_level = pokemon['level']
    pokemon_cpm = team_creator.cp_multipliers[pokemon_level]
    stat_value = float(pokemon.get('baseStats').get(stat) + pokemon['ivs'][0 if stat == 'atk' else 1]) * pokemon_cpm
    return stat_value


def calculate_move_damage(move, attacker, defender, team_creator):
    """
    Returns the amount of damage a move does from the attacker to the defender.
    The pokemon level and ivs are determined by the default ivs for the chosen league
    """
    attack = get_pokemon_stat(attacker, team_creator, 'atk')
    defense = get_pokemon_stat(defender, team_creator, 'def')

    '''
    attacker_level = attacker['level']
    defender_level = defender['level']
    attacker_cpm = team_creator.cp_multipliers[attacker_level]
    defender_cpm = team_creator.cp_multipliers[defender_level]
    attack = float(attacker.get('baseStats').get('atk') + attacker['ivs'][0]) * attacker_cpm
    defense = float(defender.get('baseStats').get('def') + defender['ivs'][1]) * defender_cpm
    '''
    power = float(move.get('power'))

    stab = 1.2 if move.get('type') in attacker.get('types') else 1.0
    effectiveness = float(team_creator.get_effectiveness(move.get('type'), defender.get('types')))

    # PVPoke uses a bonus multiplier value. Not sure why..
    # https://github.com/pvpoke/pvpoke/blob/master/src/js/battle/Battle.js#L221
    bonus_multiplier = 1.3 # UPDATE: this is because PVP damage is 1.3x power
    print(f"{move.get('moveId')} effectiveness: {effectiveness}")
    print(f"p: {power} - a: {attack} - d: {defense} - s: {stab} - e: {effectiveness}")
    return math.floor(0.5 * power * attack / defense * stab * effectiveness * bonus_multiplier) + 1


def status_damage(damage, att_status, def_status):
    """
    Return the total damage given status boosts/debuffs

    :damage: current damage before buffs/debuffs
    :att_status: attack status of attacking pokemon
    :def_status: def status of defending pokemon

    boost/def based on (boost + 4)/4 and 4/(debuff + 4)
    i.e. 
      +1 att means att pokemon does 5/4 damage
      -1 def means pokemon takes 5/4 dmg from opponent
      -1 att means att pokemon does 4/5 damage
      +1 def means opponent does 4/5 damage
    """
    dmg = lambda x: ((float(x) if x > 0 else 0.0) + 4.0) / ((float(x) if x < 0 else 0.0) + 4.0)
    att_dmg, def_dmg = dmg(att_status), dmg(def_status)
    damage = float(damage)
    return math.floor((damage - 1.0) * (att_dmg * def_dmg)) + 1.0


def sim_battle(pokemon1, pokemon2, team_creator, shields=[1,1]):
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
    p1_chargemove2['damage'] = move1_damage[p1_chargemove2['moveId']]
    p1_count1 = p1_chargemove1['energy'] / p1_fastmove['energyGain']
    p1_count2 = p1_chargemove2['energy'] / p1_fastmove['energyGain']
    print(f"pokemon1 counts: {p1_count1} {p1_count2}")
    p1_moveset = Moveset(p1_fastmove, p1_chargemove1, p1_chargemove2)

    # calculate number of pokemon2 fast moves to charge moves
    p2_fastmove = pokemon2_moves[movesets[pokemon2][0]]
    p2_fastmove['damage'] = move2_damage[p2_fastmove['moveId']]
    p2_chargemove1 = pokemon2_moves[movesets[pokemon2][1]]
    p2_chargemove1['damage'] = move2_damage[p2_chargemove1['moveId']]
    p2_chargemove2 = pokemon2_moves[movesets[pokemon2][2]]
    p2_chargemove2['damage'] = move2_damage[p2_chargemove2['moveId']]
    p2_count1 = p2_chargemove1['energy'] / p2_fastmove['energyGain']
    p2_count2 = p2_chargemove2['energy'] / p2_fastmove['energyGain']
    print(f"pokemon2 counts: {p2_count1} {p2_count2}")
    p2_moveset = Moveset(p2_fastmove, p2_chargemove1, p2_chargemove2)

    p1_health = math.floor((pokemon1_data['baseStats']['hp']+pokemon1_data['ivs'][2])*team_creator.cp_multipliers[pokemon1_data['level']])
    p2_health = math.floor((pokemon2_data['baseStats']['hp']+pokemon2_data['ivs'][2])*team_creator.cp_multipliers[pokemon2_data['level']])
    print(f"p1 health: {p1_health} - p2 health: {p2_health}")
    healths = {pokemon1: p1_health, pokemon2: p2_health}

    # THE BATTLE
    turns = 0
    pokemons = [
        #Pokemon(pokemon1, p1_health, p1_fastmove, p1_chargemove1, shields[0], pokemon1_data),
        #Pokemon(pokemon2, p2_health, p2_fastmove, p2_chargemove1, shields[1], pokemon2_data)
        Pokemon(pokemon1, p1_health, shields[0], pokemon1_data, p1_moveset),
        Pokemon(pokemon2, p2_health, shields[1], pokemon2_data, p2_moveset)
    ]

    # sort pokemon by higher attack to lower
    pokemons.sort(key=lambda x: get_pokemon_stat(x.data, team_creator, 'atk'), reverse=True)

    print(f"{pokemons[0].id}: {pokemons[0].fastmove_turns}")
    print(f"{pokemons[1].id}: {pokemons[1].fastmove_turns}")
    battle_text = []

    battle_function(pokemons, battle_text)
    while pokemons[0].health > 0 and pokemons[1].health > 0:
        turns += 1
        health_text = f"{turns}: {pokemons[0]}\t{pokemons[1]}"
        print(health_text)
        battle_text.append(health_text)
        for num, pokemon in enumerate(pokemons):
            # skip if the pokemon fainted
            if pokemon.health <= 0:
                continue
            other_pokemon = pokemons[1 - num % 2]

            '''
            pokemon.turns += 1
            if pokemon.done_attacking():
                pokemon.turns = 0
                pokemon.attack()
                other_pokemon.damage(pokemon.moveset.fast['damage'])
            '''
            # determine if fast move is done
            if turns * 500 % pokemon.moveset.fast['cooldown'] == 0:
                # keep track of other pokemon health
                #pokemons[1-num%2].damage(pokemon.moveset.fast['damage'])
                other_pokemon.damage(pokemon.moveset.fast['damage'])

                # Keep track of energy
                pokemon.attack()

                # throw charge move
                thrown_charge = pokemon.check_charge(opponent_shields=other_pokemon)
                #if pokemon.check_charge():
                if thrown_charge:
                    charge_text = f"{pokemon} threw {thrown_charge['moveId']}"
                    print(charge_text)
                    battle_text.append(charge_text)
                    pokemon.energy -= thrown_charge['energy']
                    pokemon.charge_moves_thrown += 1
                    #if not pokemons[1-num%2].take_charge(thrown_charge['damage']):
                    if not other_pokemon.take_charge(thrown_charge['damage']):
                        #shield_text = f"{pokemons[1-num%2].id} used a shield"
                        shield_text = f"{other_pokemon.id} used a shield"
                        print(shield_text)
                        battle_text.append(shield_text)
        
        # No sneaks occur if one pokemon is dead from charge move
        if pokemons[0].health == 0 or pokemons[1].health == 0:
            continue
        # determine if sneaks occcured
        # check alignment of fast move timing
        if pokemons[0].fastmoves_thrown * pokemons[0].fastmove_turns == pokemons[1].fastmoves_thrown * pokemons[1].fastmove_turns:
            # if both pokemon throw charge at same time then no sneaks
            # pokemons 1 sneak
            if pokemons[0].charge_thrown and not pokemons[1].charge_thrown:
                pokemons[1].attack()
                pokemons[0].damage(pokemons[1].moveset.fast['damage'])
                print(f"{pokemons[1]} got to sneak a fast move ({pokemons[1].moveset.fast['moveId']})")
            # pokmeon 0 sneak
            if pokemons[1].charge_thrown and not pokemons[0].charge_thrown:
                pokemons[0].attack()
                pokemons[1].damage(pokemons[0].moveset.fast['damage'])
                print(f"{pokemons[0]} got to sneak a fast move ({pokemons[0].moveset.fast['moveId']})")
        
        # Reset the fastmove counts if any charge moves are thrown
        if pokemons[0].charge_thrown or pokemons[1].charge_thrown:
            pokemons[0].fastmoves_thrown = 0
            pokemons[1].fastmoves_thrown = 0
            pokemons[0].charge_thrown = False
            pokemons[1].charge_thrown = False
                    


    finishing_text = f"{pokemons[0]}\t{pokemons[1]}"
    print(finishing_text)
    battle_text.append(finishing_text)

    winner = pokemon1
    if pokemons[0].health <= 0:
        #winner = pokemon2
        winner = pokemons[1].id
        leftover_health =  float(pokemons[1].health)/ healths[winner]
    else:
        winner = pokemons[0].id
        leftover_health =  float(pokemons[0].health) / healths[winner]
    finishing_text = f"{winner} won with {leftover_health*100:.2f}% health remaining!"
    print(finishing_text)
    battle_text.append(finishing_text)
    
    return winner, leftover_health, battle_text


def is_fast_move_done(pokemon, turns):
    """
    Determine if the fast move finished
    """
    return ((turns - 1)*500) % pokemon.moveset.fast['cooldown'] == 0


def attack(att_pokemon, def_pokemon, stop_event, turn_event, other_turn_event, str_events):
    """
    :param att_pokemon: the attacking pokemon
    :param def_pokemon: the defending pokemon
    :param stop_event: stop if a charge move is being thrown
    :param turn_event: event to indicate a turn is finished
    :param other_turn_event: event to indicate other pokemon is done with turn
    :param str_events: dict (b.c thread safe) containing all text events
    """
    turns = 0
    while def_pokemon.health > 0:
        turn_event.clear()
        #print(f"cleared turn for {att_pokemon.id}")
        time.sleep(0.1)
        turns += 1
        att_pokemon.turns = turns
        '''
        # check at beginning of turn if a charge move can be thrown
        thrown_charge = att_pokemon.check_charge()
        if thrown_charge:
            text = f"[{turns-1}] {att_pokemon.id} is throwing a charge move"
            print(text)
            str_events[att_pokemon.id].append(text)
            stop_event.set()
        '''

        # Stop if a charge move is being thrown by either pokemon
        if stop_event.is_set():
            print(f"Stopped inside {att_pokemon.id} at turn {turns}")
            turn_event.set()

            # if finished with a fast move then sneak a move
            if is_fast_move_done(att_pokemon, turns) and is_fast_move_done(def_pokemon, turns):
                att_pokemon.attack()
                damage = att_pokemon.moveset.fast['damage']
                if att_pokemon.att_status or def_pokemon.def_status:
                    damage = status_damage(damage, att_pokemon.att_status, def_pokemon.def_status)
                def_pokemon.damage(damage)
                text = f"[{turns-1}] {att_pokemon} sneaked attacked {def_pokemon} with {att_pokemon.moveset.fast['moveId']}"
                print(text)
                str_events[att_pokemon.id].append(text)

            return

        #if (turns*500) % att_pokemon.moveset.fast['cooldown'] != 0:
        #    print(f"[{turns+1}] Waiting for {att_pokemon.id} to attack with {att_pokemon.moveset.fast['moveId']}")
        if ((turns - 1)*500) % att_pokemon.moveset.fast['cooldown'] == 0:
            # Check if a charge move can be thrown, else throw a fast move
            thrown_charge = att_pokemon.check_charge(opponent_shields=def_pokemon.shields, opponent_damage=def_pokemon.moveset.fast['damage'])
            if thrown_charge:
                text = f"[{turns-1}] {att_pokemon} is throwing a charge move"
                print(text)
                str_events[att_pokemon.id].append(text)
                stop_event.set()
            else:
                # keep track of energy
                att_pokemon.attack()

                # damage opponent
                damage = att_pokemon.moveset.fast['damage']

                # apply boosts/debuffs
                if att_pokemon.att_status or def_pokemon.def_status:
                    damage = status_damage(damage, att_pokemon.att_status, def_pokemon.def_status)
                #damage = att_pokemon.moveset.fast['damage'] * att_pokemon.att_status
                def_pokemon.damage(damage)
                text = f"[{turns-1}] {att_pokemon} attacked {def_pokemon} with {att_pokemon.moveset.fast['moveId']}"
                print(text)
                str_events[att_pokemon.id].append(text)

        turn_event.set()
        #print(f"Set turn for {att_pokemon.id}")
        waited = other_turn_event.wait(10)
        if not waited:
            print(f"****{att_pokemon} waited too long for turn to be done")




def battle_function(pokemons: list, battle_text: list) -> list:
    """
    :param pokemons: a list of two pokemon
    :param battle_text: the updated battle text
    """
    turns = 0
    stop_event = threading.Event()
    
    print(f"{pokemons[0]} - {pokemons[1]}")
    while pokemons[0].health > 0 and pokemons[1].health > 0:
        turn1_event = threading.Event()
        turn2_event = threading.Event()
        str_events = {p.id: [] for p in pokemons}
        turns += 1
        if turns > 10:
            print("Cancelling out because too many charges thrown")
            return
        p1_thread = threading.Thread(
            target=attack,
            args=(pokemons[0], pokemons[1], stop_event, turn1_event, turn2_event, str_events,)
        )
        p2_thread = threading.Thread(
            target=attack,
            args=(pokemons[1], pokemons[0], stop_event, turn2_event, turn1_event, str_events,)
        )
        p1_thread.start()
        p2_thread.start()

        p1_thread.join()
        p2_thread.join()

        if stop_event.is_set():
            stop_event.clear()
            print("Stopped outer loop")
            print(f"{pokemons[0]} - {pokemons[1]}")

            # pokeons[0] has higher attack 
            for i in range(len(pokemons)):
                att_pokemon = pokemons[i]
                def_pokemon = pokemons[1 - i % 2]
                if att_pokemon.charge_thrown and att_pokemon.health > 0:
                    # check if defending pokemon sneaks a move
                    '''
                    print(f"{def_pokemon} turns: {def_pokemon.turns} - cooldown: {def_pokemon.moveset.fast['cooldown']}")
                    if not def_pokemon.charge_thrown and (def_pokemon.turns * 500) % def_pokemon.moveset.fast['cooldown'] == 0:
                        def_pokemon.attack()
                        att_pokemon.damage(def_pokemon.moveset.fast['damage'])
                        print(f"{def_pokemon} snuck a move on {att_pokemon}")
                    '''

                    # throw charge
                    thrown_charge = att_pokemon.check_charge(opponent_shields=def_pokemon.shields, opponent_damage=def_pokemon.moveset.fast['damage'])
                    #thrown_charge = att_pokemon.check_charge()
                    att_pokemon.energy -= thrown_charge['energy']
                    att_pokemon.charge_moves_thrown += 1
                    att_pokemon.charge_thrown = False
                    text = f"{att_pokemon.id} threw {thrown_charge['moveId']}"
                    print(text)
                    str_events[att_pokemon.id].append(f"[{att_pokemon.turns}] {text}")

                    # calculate damage based on boosts/debuffs
                    damage = thrown_charge['damage']
                    if att_pokemon.att_status or def_pokemon.def_status:
                        damage = status_damage(damage, att_pokemon.att_status, def_pokemon.def_status)

                    # Check if defending pokemon used shield
                    if not def_pokemon.take_charge(damage):
                        shield_text = f"{def_pokemon.id} used a shield"
                        print(shield_text)
                        battle_text.append(shield_text)
                        str_events[def_pokemon.id].append(f"[{def_pokemon.turns}] {shield_text}")

                    # apply possible buggs or debuffs
                    if thrown_charge.get('buffApplyChance') and thrown_charge.get('buffs'):
                        chance = float(thrown_charge.get('buffApplyChance'))
                        buffs = thrown_charge.get('buffs')
                        if ALWAYS_BUFF or random.random() <= chance:
                            archetype = thrown_charge.get('archetype', '')
                            if "Self" in archetype or 'Boost' in archetype and thrown_charge['name'] != 'Obstruct':
                                att_pokemon.att_status += int(buffs[0])
                                att_pokemon.def_status += int(buffs[1])
                                text = f"{att_pokemon.id} boost! [{att_pokemon.att_status}, {att_pokemon.def_status}]"
                                print(text)
                                str_events[att_pokemon.id].append(f"[{att_pokemon.turns}] {text}")
                            else:
                                print(f"{def_pokemon.id} debuff!")
                                def_pokemon.att_status += int(buffs[0])
                                def_pokemon.def_status += int(buffs[1])
                                text = f"{def_pokemon.id} debuff! [{def_pokemon.att_status}, {def_pokemon.def_status}]"
                                print(text)
                                str_events[def_pokemon.id].append(f"[{def_pokemon.turns}] {text}")
                            # Obstruct is special
                            if thrown_charge['name'] == "Obstruct":
                                self_buff = thrown_charge.get('buffsSelf', [0, 0])
                                att_pokemon.att_status += int(self_buff[0])
                                att_pokemon.def_status += int(self_buff[1])
                                text = f"{att_pokemon.id} boost! [{att_pokemon.att_status}, {att_pokemon.def_status}]"
                                print(text)
                                str_events[att_pokemon.id].append(f"[{att_pokemon.turns}] {text}")

                    if def_pokemon.health <= 0:
                        text = f"{def_pokemon.id} fainted"
                        print(text)
                        str_events[def_pokemon.id].append(f"[{def_pokemon.turns}] {text}")
                        break
            #print(str_events)
            print("\n\n")
            print(print_turns(str_events))
            print("\n\n")
            

def print_turns(str_events):
    turns = {}
    for p, p_events in str_events.items():
        for event in p_events:
            res = re.findall(r'\[([0-9]*)\] (.*)', event)
            if res:
                turn, string = res[0]
                if turn not in turns:
                    turns[turn] = []
                turns[turn].append(string)

    final_string = []
    for turn in sorted(list(turns.keys()), key=lambda x: int(x)):
        turn_str = '  -  '.join(turns[turn])
        final_string.append(f"[{turn}] {turn_str}")
    return '\n'.join(final_string)


if __name__ == '__main__':
    from application.pokemon.team_building import MetaTeamDestroyer, TeamCreater
    print("Initializing data...")
    team_creator = MetaTeamDestroyer(league="GL")
    tc = TeamCreater(team_creator)

    print("Simulating battle")
    #results = sim_battle('stunfisk_galarian', 'venusaur', tc)
    #results = sim_battle('stunfisk_galarian', 'scrafty', tc)
    #results = sim_battle('scrafty', 'stunfisk_galarian', tc)
    #results = sim_battle('stunfisk_galarian', 'scrafty', tc)
    #results = sim_battle('medicham', 'wigglytuff', tc, shields=[0, 0])
    #results = sim_battle('venusaur', 'ferrothorn', tc)

    results = sim_battle("medicham", "lanturn", tc)
    #results = sim_battle("medicham", "scrafty", tc)
    print(results[0], results[1])
    #sim_battle('stunfisk_galarian', 'dialga', tc)
    #sim_battle('talonflame', 'dialga', tc)
