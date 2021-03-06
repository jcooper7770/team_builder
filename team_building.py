"""

 Team generator based on the current meta

 1. Get the most common leads / back lines
 2. Choose lead based on common leads.
 3. Choose back line based on back line
 
 for questions email: aaron@gobattlelog.com
 pvpoke github: https://github.com/pvpoke/pvpoke

 images of pokemon: https://img.pokemondb.net/sprites/black-white/normal/charizard.png

 TODO:
  - create my own counters lists instead of the 5 from pvpoke
  - [DONE] create smart team comp (with ABB option)
  - [DONE?] host online somewhere
  - [DONE] weighted output based on date reported
      - choose # days of reportings
      - choose last X reportings
  - [DONE] Pick SS or closer instead of lead
  - Google app engine / google cloud run for free hosting
  - Add to html: please input more data to gobattlelog
      - all this possible to people entering data./ Aaron is grateful to them
  - check out amgesus.tar.gz in our #computer-science channel. It shows how to run all of pvpoke'sscripts from the comand line.
  - [DONE] Click on a pokmeon and simulate a battle in pvpoke
     - https://pvpoke.com/battle/1500/{pokemon1}/{pokemon2}/{#shields1}{#shields2}
"""

import json
import random
import requests
from datetime import datetime, timedelta
from collections import defaultdict


# The number of pokemon to consider
TOP_TEAM_NUM = None
MIN_COUNTERS = 25
TOP_PERCENT = 1
REQUEST_TIMEOUT = 180

LEAGUE_RANKINGS = {
    "ULP": "https://vps.gobattlelog.com/data/overall/rankings-2500-premier.json?v=1.25.10",
    "ULPC": "https://vps.gobattlelog.com/data/overall/rankings-2500-premierclassic.json?v=1.25.10",
    "UL": "https://vps.gobattlelog.com/data/overall/rankings-2500.json?v=1.25.10",
    "ML": "https://vps.gobattlelog.com/data/overall/rankings-10000.json?v=1.25.31",
    "MLC": "https://vps.gobattlelog.com/data/overall/rankings-10000-classic.json?v=1.25.31",
    "MLPC": "https://vps.gobattlelog.com/data/overall/rankings-10000-premierclassic.json?v=1.25.31",
    "Element": "https://vps.gobattlelog.com/data/overall/rankings-500-element.json?v=1.25.31",
    "Remix": "https://vps.gobattlelog.com/data/overall/rankings-1500-remix.json?v=1.25.35",
    "ULRemix": "https://vps.gobattlelog.com/data/overall/rankings-2500-remix.json?v=1.25.35",
    "GL": "https://vps.gobattlelog.com/data/overall/rankings-1500.json?v=1.25.35",
    "Jungle": "https://vps.gobattlelog.com/data/overall/rankings-500-littlejungle.json?v=1.28.0",
    "Halloween": "https://vps.gobattlelog.com/data/overall/rankings-1500-halloween.json?v=1.25.35",
    "Kanto":"https://vps.gobattlelog.com/data/overall/rankings-1500-kanto.json?v=1.25.35",
    "Holiday":"https://vps.gobattlelog.com/data/overall/rankings-1500-holiday.json?v=1.25.35",
    "Sinnoh": "https://vps.gobattlelog.com/data/overall/rankings-1500-sinnoh.json?v=1.25.35",
    "Love": "https://vps.gobattlelog.com/data/overall/rankings-1500-love.json?v=1.25.35"
}
LEAGUE_DATA = {
    "ULP": "https://vps.gobattlelog.com/records/ultra-premier/latest.json?ts=449983.3",
    "ULPC": "https://vps.gobattlelog.com/records/ultra-premierclassic/latest.json?ts=449983.3",
    #"UL": "https://vps.gobattlelog.com/records/ultra/latest.json?ts=449983.3",
    "UL": "https://vps.gobattlelog.com/records/ultra/latest.json?ts=452212.3",
    "GL": "https://vps.gobattlelog.com/records/great/latest.json?ts=450364.2",
    "Kanto": "https://vps.gobattlelog.com/records/great-kanto/latest.json?ts=450364.2",
    "ML": "https://vps.gobattlelog.com/records/master/latest.json?ts=451466.3",
    "MLC": "https://vps.gobattlelog.com/records/master/latest.json?ts=451466.3",
    "MLPC": "https://vps.gobattlelog.com/records/master-premierclassic/latest.json?ts=451466.3",
    "Element": "https://vps.gobattlelog.com/records/element/latest.json?ts=451466.3",
    "Remix": "https://vps.gobattlelog.com/records/great-remix/latest.json?ts=451709.1",
    "ULRemix": "https://vps.gobattlelog.com/records/ultra-remix/latest.json?ts=451709.1",
    "Jungle": "https://vps.gobattlelog.com/records/littlejungle/latest.json?ts=451709.1",
    "Halloween": "https://vps.gobattlelog.com/records/great-halloween/latest.json?ts=451466.3",
    "Kanto": "https://vps.gobattlelog.com/records/great-kanto/latest.json?ts=451466.3",
    "Holiday": "https://vps.gobattlelog.com/records/great-holiday/latest.json?ts=451466.3",
    "Sinnoh": "https://vps.gobattlelog.com/records/great-sinnoh/latest.json?ts=451466.3",
    "Love": "https://vps.gobattlelog.com/records/great-love/latest.json?ts=451466.3"
}
LEAGUE_VALUE = {
    'GL': '1500',
    'Remix': '1500',
    'UL': '2500',
    'ULRemix': '2500',
    'ULP': '2500',
    'ULPC': '2500',
    'ULPC': '2500-40',
    'MLC': '10000-40',
    'MLPC': '10000-40',
    'ML': '10000',
    'Element': '500',
    'Jungle': '500',
    'Halloween': '1500',
    'Kanto': '1500',
    'Holiday': '1500',
    'Sinnoh': '1500',
    "Love": '1500'
}
CUP_VALUE = {
    'MLC': 'classic',
    'ULRemix': 'remix',
    'Jungle': 'littlejungle',
    'ULPC': 'premierclassic',
    'MLPC': 'premierclassic',
    'Halloween': 'halloween',
    'Kanto': 'kanto',
    'Holiday': 'holiday',
    'Sinnoh': 'sinnoh',
    'Love': 'love'
}

# https://gamepress.gg/pokemongo/cp-multiplier
HIGH_MULTIPLIERS = {
    45.5: 0.81779999,
    46: 0.82029999,
    46.5: 0.82279999,
    47: 0.82529999,
    47.5: 0.82779999,
    48: 0.83029999,
    48.5: 0.83279999,
    49: 0.83529999,
    49.5: 0.83779999,
    50: 0.84029999,
    50.5: 0.84279999,
    51: 0.84529999
}

class NoPokemonFound(Exception):
    pass

class TeamCreater:
    def __init__(self, team_maker):
        self.types = requests.get("https://pogoapi.net//api/v1/type_effectiveness.json").json()
        cp_multipliers = requests.get("https://pogoapi.net//api/v1/cp_multiplier.json").json()
        self.cp_multipliers = {cpm['level']:cpm['multiplier'] for cpm in cp_multipliers}
        self.cp_multipliers.update(HIGH_MULTIPLIERS)
        self.team_maker = team_maker

    def get_effectiveness(self, attacker_type, defender_types):
        """ Returns the effectiveness of attack type on defender types """
        effectiveness = 1
        for defender_type in defender_types:
            if defender_type != 'none':
                effectiveness *= self.types[attacker_type.capitalize()][defender_type.capitalize()]
        return effectiveness

    def get_weaknesses(self, pokemon):
        """ Returns the type weaknesses of a given pokemon """
        weaks = {}
        for p in self.team_maker.game_master.get('pokemon'):
            if p.get('speciesId') != pokemon:
                continue
            pokemon_types = p.get('types')

            weaknesses = set()
            weaknesses_dict = defaultdict(lambda: 1)
            for t in pokemon_types:
                if t == 'none':
                    continue
                for chart_type, chart_effectiveness in self.types.items():
                    type_effectiveness = chart_effectiveness[t.capitalize()]
                    # Type effectiveness is a multiplier value
                    weaknesses_dict[chart_type] *= type_effectiveness

                    if chart_effectiveness[t.capitalize()] > 1:
                        weaknesses.add(chart_type.lower())
            weaks = {x:y for x,y in weaknesses_dict.items() if y>1.0}
            #print(f"{pokemon} is weak to {weaknesses}")
            #print(f"{pokemon} weaknesses: {weaks}")
        return weaks

class MetaTeamDestroyer:
    """
    Creator of teams to destroy the meta
    """
    def __init__(self, rating=None, league="GL", days_back=None, num_reports=None):
        """
        :param rating: The rating to get the data from (Default: None)
        :type rating: int
        :param league: The league to check (Default: "ULP")
        :type league: str
        :param days_back: The number of days back to get data (Default: None)
        :type days_back: int
        :param num_reports: The number of latest reports to check (Default: None)
        :type num_reports: int
        """
        # Initialize all of the data
        rankings_url = LEAGUE_RANKINGS.get(league)
        latest_url = LEAGUE_DATA.get(league)
        self.result_data = {}

        # Get the latest-large data
        latest_url = latest_url.replace('latest', 'latest-large')
        self.league = league
        self.league_cp = LEAGUE_VALUE[league]

        try:
            self.all_pokemon = requests.get(rankings_url, timeout=REQUEST_TIMEOUT).json()
            json.dump(self.all_pokemon, open("data/pokemon_rankings.json", 'w'))
        except Exception as exc:
            print(f"Failed to load ranking data because: {exc}")
            self.all_pokemon = json.load(open("data/pokemon_rankings.json"))

        try:
            self.game_master = requests.get("https://vps.gobattlelog.com/data/gamemaster.json?v=1.25.10", timeout=REQUEST_TIMEOUT).json()
            json.dump(self.game_master, open("game_master.json"))
        except Exception as exc:
            print(f"Failed to load game master data because: {exc}")
            self.game_master = json.load(open("game_master.json"))

        try:
            self.latest_info = requests.get(latest_url, timeout=REQUEST_TIMEOUT).json().get("records")
            json.dump(self.latest_info, open(f"data/latest_{league}.json", 'w'))
        except Exception as exc:
            print(f"Failed to load latest data because: {exc}")
            self.all_pokemon = json.load(open(f"data/latest_{league}.json"))

        # Sort reports by time and get last X teams
        sorted_latest_info = sorted(self.latest_info, key=lambda x: x.get('time'), reverse=True)
        if num_reports:
            if len(sorted_latest_info) > num_reports - 1:
                self.latest_info = sorted_latest_info[:num_reports]
            else:
                self.latest_info = sorted_latest_info

        # Round the rating if one is provided
        if rating:
            rating = int(round(rating/1000., 1)*1000)


        # Filter out values based on date and rating
        temp_latest_info = []
        if days_back or rating:
            for record in self.latest_info:
                if days_back:
                    if datetime.fromtimestamp(record.get('time')) < datetime.now() - timedelta(days=days_back):
                        continue
                if rating:
                    if record.get('rating') != rating:
                        continue
                temp_latest_info.append(record)
            self.latest_info = temp_latest_info

        if len(self.latest_info) == 0:
            raise NoPokemonFound(f"Did not find {league} data last {days_back} days at {rating or 'all'} rating")
                    


        # Create common leads and backlines lists
        leads = defaultdict(int)
        safeswaps = defaultdict(int)
        backs = defaultdict(int)
        for record in self.latest_info:
            if rating and record.get("rating") != rating:
                continue
            team = record.get("oppo_team")
            pokemon = team.split('/')
            leads[pokemon[0].split(':')[0]] += 1
            safeswaps[pokemon[1].split(':')[0]] += 1
            backs[pokemon[2].split(':')[0]] += 1

        self.leads_list = sorted(list(leads.items()), key=lambda x: x[1], reverse=True)
        self.safeswaps_list = sorted(list(safeswaps.items()), key=lambda x: x[1], reverse=True)
        self.backs_list = sorted(list(backs.items()), key=lambda x: x[1], reverse=True)

        # Remove pokemon not in the top TOP_PERCENT from the leads
        if TOP_PERCENT:
            self.leads_list = self.filter_top_pokemon(self.leads_list)
            self.safeswaps_list = self.filter_top_pokemon(self.safeswaps_list)
            self.backs_list = self.filter_top_pokemon(self.backs_list)
        

        # Create a mapping of the counters
        self.species_counters_dict = defaultdict(set)# pokemon that each pokemon counters well
        self.species_weaknesses_dict = defaultdict(set)# pokemon that each pokemon is weak to
        self.species_moveset_dict = defaultdict(list)
        for species in self.all_pokemon:
            counters = species.get('counters')
            matchups = species.get('matchups')
            species_id = species.get('speciesId')
            self.species_counters_dict[species_id].update([c.get('opponent') for c in counters])
            self.species_weaknesses_dict[species_id].update([m.get('opponent') for m in matchups])

            # Add the species as counters to the matchups
            for matchup in matchups:
                self.species_counters_dict[matchup.get('opponent')].add(species_id)

            for counter in counters:
                self.species_weaknesses_dict[counter.get('opponent')].add(species_id)
        
            # Add the movesets
            self.species_moveset_dict[species.get('speciesId')] = species.get('moveset')

    @staticmethod
    def filter_top_pokemon(pokemon_list):
        """
        Filter out the top TOP_PERCENT of pokemon from the list
        """
        total_num = sum([pokemon[1] for pokemon in pokemon_list])
        min_allowed = TOP_PERCENT/100.0 * total_num
        return [pokemon for pokemon in pokemon_list if pokemon[1] > min_allowed]
        
    def get_default_ivs(self, pokemon, league):
        """
        Get default ivs from the game master for the given pokmeon
        """
        league_cp = LEAGUE_VALUE.get(league, '1500').split('-')[0]
        if league_cp == '10000':
            return '15-15-15'
        for pokemon_info in self.game_master.get('pokemon'):
            if pokemon_info.get('speciesId') == pokemon:
                print(pokemon_info.get('defaultIVs'))
                print(league_cp)
                print(pokemon_info.get('defaultIVs').get(f'cp{league_cp}', 'cp1500'))
                return '-'.join([str(n) for n in pokemon_info.get('defaultIVs').get(f'cp{league_cp}', 'cp1500')[1:]])

    def get_counters(self, pokemon_name):
        """
        returns the counters to the given pokemon

        Change this to create the counters from the game_master
        """
        # Simulate battles against ALL pokemon
        #for pokemon in self.all_pokemon:
        #    simulate_battle(pokemon.get('speciesId'), pokemon_name)
        return self.species_counters_dict[pokemon_name]

    def get_reccommended_counters(self, pokemon_list):
        """ Returns recommended counters to the list of pokemon """
        # Only focus on top leads
        if TOP_TEAM_NUM:
            pokemon_list = pokemon_list[:TOP_TEAM_NUM]

        # Get counters to the common leads
        # pokemon_list = [('mon1', # of times reported) ...]
        # counter_leads = [['mon1', 'mon2' ..], ...]
        counter_leads = []
        total_reported_pokemon = 0
        for lead in pokemon_list:
            #counters = list(self.get_counters(lead[0]))
            
            #counters = self.get_counters(lead[0])
            counters = list(self.get_counters(lead[0])) * lead[1]
            counter_leads.append(counters)

            total_reported_pokemon += lead[1]

        # Get the most common pokemon from the counters
        counter_counts = defaultdict(int)
        for counters in counter_leads:
            for counter in counters:
                counter_counts[counter] += 1

        # Convert counts to percents
        for count in counter_counts:
            #counter_counts[count] = 100.*counter_counts[count] / float(len(pokemon_list))
            counter_counts[count] = 100.*counter_counts[count] / float(total_reported_pokemon)

        # Get the counters in the form of
        #  [('p1', #,), ('p2', #), ...]
        counter_counts_list = sorted(
            list(counter_counts.items()),
            key=lambda x: x[1],
            reverse=True
        )
        return counter_counts_list

    def get_moveset_string(self, pokemon_name, moveset):
        """
        Returns the moveset string for the pvpoke url based on the moveset
        """
        moves = []
        for pokemon in self.game_master.get("pokemon"):
            if pokemon["speciesId"] == pokemon_name:
                # fast move
                for n, move in enumerate(pokemon['fastMoves']):
                    if move == moveset[0]:
                        moves.append(str(n))
            
                # charged moves
                for move in moveset[1:]:
                    for n, m in enumerate(pokemon['chargedMoves']):
                        if m == move:
                            moves.append(str(n+1))
        return '-'.join(moves)


    def simulate_battle(pokemon1, pokemon2, n_shields=1):
        """
        last numbers are the movesets..
        to get default movesets use pvpoke rankings and the game master to get the numbers
        """
        moveset1 = self.species_moveset_dict[pokemon1]
        moveset2 = self.species_moveset_dict[pokemon2]
        moveset_str1 = self.get_moveset_string(pokemon1, moveset1)
        moveset_str2 = self.get_moveset_string(pokemon2, moveset2)
        url = f"https://pvpoke.com/battle/2500/{pokemon1}/{pokemon2}/${n_shields}${n_shields}/{moveset_str1}/{moveset_str2}/"
        requests.get(url)
        pass

    def choose_weighted_pokemon(self, pokemon_list, n=1):
        """
        Chooses pokemon from the list [(p1, #), (p2, #), ...]
        """
        weights, pokemons = [], []
        for pokemon in pokemon_list:
            # Skip any pokemon which don't counter enough pokemon
            if MIN_COUNTERS and pokemon[1] < MIN_COUNTERS:
                continue

            pokemons.append(pokemon[0])
            weights.append(pokemon[1])

        # Return all pokemon if none counter enough pokemon
        if not pokemons:
            pokemons = [pokemon[0] for pokemon in pokemon_list]
            weights = [pokemon[1] for pokemon in pokemon_list]
        try:
            random_pokemons = random.choices(pokemons, weights=weights, k=n)
        except Exception as exc:
            raise Exception(f"{n} - {pokemon_list} - {exc}")
        return random_pokemons

    def recommend_team(self, chosen_pokemon=None, position="lead"):
        """
        Returns a team around a random lead mon picked from the anti-meta list.
        After picking a lead, the two back pokemon are chosen as counters to the lead's weaknesses
        """
        if chosen_pokemon:
            if position == 'lead':
                return self.build_team_from_pokemon(chosen_pokemon)
            elif position == 'back':
                return self.build_safeswap_team(chosen_pokemon)
        print("Choosing a random lead from the leads list")
        lead_counters = self.get_reccommended_counters(self.leads_list)
        random_counter = self.choose_weighted_pokemon(lead_counters)[0]
        return self.build_team_from_pokemon(random_counter)

    def build_safeswap_team(self, pokemon):
        """
        Builds a team with the given pokemon in the back
        Note: squares the weights for more weight on common pokemon
        """
        # Determine pokemon weakness typings
        tc = TeamCreater(self)
        ss_type_weaknesses = tc.get_weaknesses(pokemon)

        # Find pokemon that the given pokemon counters
        counters = [p for p, counters in self.species_counters_dict.items() if pokemon in counters]
        print(f"Pokemon that {pokemon} counters: {counters}")

        # Find a pokemon weak to the countered pokemon
        all_weak_pokemon = [weak_pokemon for counter in counters for weak_pokemon in self.species_counters_dict[counter]]

        # Only keep pokemon with different weaknesses
        weak_kept_pokemon = []
        for p in set(all_weak_pokemon):
            pokemon_weaknesses = tc.get_weaknesses(p)
            if len(set(pokemon_weaknesses.keys()) - set(ss_type_weaknesses.keys())) == len(pokemon_weaknesses):
                weak_kept_pokemon.append(p)
        
        weaknesses_count = {p:weak_kept_pokemon.count(p)**2 for p in weak_kept_pokemon if p != pokemon}# {'p1': 1, 'p2':2, ...}
        weaknesses_count_list = sorted(weaknesses_count.items(), key=lambda x: x[1], reverse=True)# [(p1, 5), (p2, 4),...]
        print(f"Pokemon weak to the counters: {weaknesses_count_list}")
        random_weak_pokemon = random.choices([w[0] for w in weaknesses_count_list], weights=[w[1] for w in weaknesses_count_list], k=1)[0]
        print(f"Random chosen weak pokemon: {random_weak_pokemon}")

        # Find another pokemon strong against counters
        all_strong_pokemon = [strong_pokemon for counter in counters for strong_pokemon in self.species_weaknesses_dict[counter]]
        print(all_strong_pokemon)

        # Only keep pokmeon with similar weaknesses
        strong_kept_pokemon = []
        for p in set(all_strong_pokemon):
            pokemon_weaknesses = tc.get_weaknesses(p)
            if len(set(pokemon_weaknesses.keys()) - set(ss_type_weaknesses.keys())) != len(pokemon_weaknesses):
                strong_kept_pokemon.append(p)

        strong_count = {p:strong_kept_pokemon.count(p)**2 for p in strong_kept_pokemon if p != pokemon}
        strong_count_list = sorted(strong_count.items(), key=lambda x:x[1], reverse=True)
        print(f"Pokemon strong against countered pokemon: {strong_count_list}")

        # Only use top 25% of strong list
        #strong_count_list = strong_count_list[:len(strong_count_list)//4]
        
        random_strong_pokemon = random.choices([w[0] for w in strong_count_list], weights=[w[1] for w in strong_count_list], k=1)[0]
        print(f"Random chosen strong pokemon: {random_strong_pokemon}")

        return self.team_results([random_weak_pokemon, pokemon, random_strong_pokemon], pokemon)
        
    def team_results(self, pokemon_team, chosen_pokemon):
        """
        Returns the results of the pokemon team created
        """
        results = f"Team for {chosen_pokemon}"
        #pvpoke_link = f"https://pvpoke.com/team-builder/all/{LEAGUE_VALUE[self.league]}/{pokemon_team[0]}-m-{team_ivs[0]}%2C{pokemon_team[1]}-m-{team_ivs[1]}%2C{pokemon_team[2]}-m-{team_ivs[2]}"
        cup = CUP_VALUE.get(self.league, 'all')
        pvpoke_link = f"https://pvpoke.com/team-builder/{cup}/{LEAGUE_VALUE[self.league]}/{pokemon_team[0]}-m-0-1-2%2C{pokemon_team[1]}-m-0-1-2%2C{pokemon_team[2]}-m-0-1-2"
        results = f"{results} (<a href='{pvpoke_link}' target='_blank'>See team in pvpoke</a>)"
        team_ivs = []
        print(f"Full team:")
        for p in pokemon_team:
            print(f"    {p}: {self.species_moveset_dict[p]}")
            results = f"{results}\n{p}\t{self.species_moveset_dict[p]}"
            team_ivs.append(self.get_default_ivs(p, self.league))

        return results, pokemon_team

    def build_team_from_pokemon(self, pokemon):
        """
        Builds a team with the given pokemon by choosing counters to it's weaknesses       
        """
        print(f"Building a team around {pokemon}")
        lead_weaknesses = self.species_counters_dict[pokemon]

        # Determine pokemon weakness typings
        tc = TeamCreater(self)
        lead_type_weaknesses = tc.get_weaknesses(pokemon)
        print(f"Lead weaknesses: {lead_type_weaknesses}")
        #print(f"Weaknesses of {pokemon}: {lead_weaknesses}")

        print("Making counters to the lead weaknesses")
        lead_counters_list = [(c, 1) for c in lead_weaknesses]
        counter_counters = self.get_reccommended_counters(lead_counters_list)

        # Remove pokemon with similar weaknesses
        removed_counters = []
        for counter in counter_counters:
            pokemon_weaknesses = tc.get_weaknesses(counter[0])
            if len(set(pokemon_weaknesses.keys()) - set(lead_type_weaknesses.keys())) != len(pokemon_weaknesses):
                #print(f"Should skip {counter} with weaknesses: {pokemon_weaknesses}")
                removed_counters.append(counter[0])
        counter_counters = [counter for counter in counter_counters if counter[0] not in removed_counters]
        
        # need to pick one at a time so there are no repeats      
        back_pokemon1 = self.choose_weighted_pokemon(counter_counters)[0]
        index = [p[0] for p in counter_counters].index(back_pokemon1)
        counter_counters.pop(index)
        back_pokemon2 = self.choose_weighted_pokemon(counter_counters)[0]

        back_pokemon = sorted([back_pokemon1, back_pokemon2])
        pokemon_team = [pokemon]
        pokemon_team.extend(back_pokemon)
        return self.team_results(pokemon_team, pokemon)


def pretty_print_counters(counter_list, min_counters=None, use_percent=True):
    """ Prints the counters list nicely """
    return_text = ""
    for num, counter in enumerate(counter_list):
        if min_counters and counter[1] < min_counters:
            continue

        percent_sign = "%" if use_percent else ""
        text = f"{counter[0]:>20}: {counter[1]:<3.2f}{percent_sign}\t"
        return_text = f"{return_text}{text}"
        #print(f"{counter[0]:>20}: {counter[1]:<3.2f}{percent_sign}", end='\t')
        print(text, end='')
            
        if (num + 1) % 4 == 0:
            print()
            return_text = f"{return_text}\n"
    print()
    return return_text

def get_counters_for_rating(rating, league="ULP", days_back=None):
    """ Prints the lead, safe swap, and back line counters at the given rating """
    if league not in LEAGUE_RANKINGS:
        return f"Did not find league '{league}'"

    team_maker = MetaTeamDestroyer(rating=rating, league=league, days_back=days_back)
    #creator = TeamCreater(team_maker)
    #creator.get_weaknesses('bulbasaur')
    #creator.get_weaknesses('swampert')

    print(f"---------- Counters at {rating or 'all'} rating---------")
    print("Leads:")
    lead_counters = team_maker.get_reccommended_counters(team_maker.leads_list)
    lead_counter_text = pretty_print_counters(lead_counters, MIN_COUNTERS)

    print("\nCurrent Meta Leads:")
    lead_text = pretty_print_counters(team_maker.leads_list, use_percent=False)

    print("-----\nSafe swaps")
    ss_counters = team_maker.get_reccommended_counters(team_maker.safeswaps_list)
    ss_counter_text = pretty_print_counters(ss_counters, MIN_COUNTERS)


    print("\nCurrent Meta SS:")
    ss_text = pretty_print_counters(team_maker.safeswaps_list, use_percent=False)
    
    print("-----\nBack:")
    back_counters = team_maker.get_reccommended_counters(team_maker.backs_list)
    back_counter_text = pretty_print_counters(back_counters, MIN_COUNTERS)

    print("\nCurrent Meta Back:")
    back_text = pretty_print_counters(team_maker.backs_list, use_percent=False)

    team_maker.recommend_team()

    team_maker.result_data = {
        "good_leads": lead_counters,
        "meta_leads": team_maker.leads_list,
        "good_ss": ss_counters,
        "meta_ss": team_maker.safeswaps_list,
        "good_backs": back_counters,
        "meta_backs": team_maker.backs_list
    }
    return f"Recommended Leads\n{lead_counter_text}\nMeta leads\n{lead_text}\n\nRecommended Safe swaps\n{ss_counter_text}\nMeta Safe swaps\n{ss_text}\n\nRecommended Back\n{back_counter_text}\nMeta back\n{back_text}", team_maker


if __name__ == "__main__":
    results, team_maker = get_counters_for_rating(rating=None, league="MLC", days_back=1)
    print(results)

    #print(team_maker.build_team_from_pokemon("zapdos_shadow"))
    #for _ in range(10):
        #team_maker.build_team_from_pokemon("seviper")
        #team_maker.build_team_from_pokemon("machamp_shadow")

    safeswap_team = team_maker.build_safeswap_team("groudon")
    print(safeswap_team)
