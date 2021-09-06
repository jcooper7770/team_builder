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
  - host online somewhere
  - [DONE] weighted output based on date reported
      - choose # days of reportings
      - choose last X reportings
"""

import random
import requests
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Flask, request

app = Flask(__name__)

# The number of pokemon to consider
TOP_TEAM_NUM = None
MIN_COUNTERS = 25

LEAGUE_RANKINGS = {
    "ULP": "https://vps.gobattlelog.com/data/overall/rankings-2500-premier.json?v=1.25.10",
    "UL": "https://vps.gobattlelog.com/data/overall/rankings-2500.json?v=1.25.10",
    "ML": "https://vps.gobattlelog.com/data/overall/rankings-10000.json?v=1.25.31",
    "MLC": "https://vps.gobattlelog.com/data/overall/rankings-10000-classic.json?v=1.25.31",
    "Element": "https://vps.gobattlelog.com/data/overall/rankings-500-element.json?v=1.25.31",
    "Remix": "https://vps.gobattlelog.com/data/overall/rankings-1500-remix.json?v=1.25.35",
    "ULRemix": "https://vps.gobattlelog.com/data/overall/rankings-2500-remix.json?v=1.25.35",
    "GL": "https://vps.gobattlelog.com/data/overall/rankings-1500.json?v=1.25.35"
}
LEAGUE_DATA = {
    "ULP": "https://vps.gobattlelog.com/records/ultra-premier/latest.json?ts=449983.3",
    #"UL": "https://vps.gobattlelog.com/records/ultra/latest.json?ts=449983.3",
    "UL": "https://vps.gobattlelog.com/records/ultra/latest.json?ts=452212.3",
    "GL": "https://vps.gobattlelog.com/records/great/latest.json?ts=450364.2",
    "Kanto": "https://vps.gobattlelog.com/records/great-kanto/latest.json?ts=450364.2",
    "ML": "https://vps.gobattlelog.com/records/master/latest.json?ts=451466.3",
    "MLC": "https://vps.gobattlelog.com/records/master/latest.json?ts=451466.3",
    "Element": "https://vps.gobattlelog.com/records/element/latest.json?ts=451466.3",
    "Remix": "https://vps.gobattlelog.com/records/great-remix/latest.json?ts=451709.1",
    "ULRemix": "https://vps.gobattlelog.com/records/ultra-remix/latest.json?ts=451709.1",
}

class TeamCreater:
    def __init__(self, team_maker):
        self.types = requests.get("https://pogoapi.net//api/v1/type_effectiveness.json").json()
        self.team_maker = team_maker

    def create(self, lists_of_pokemon):
        """ Creates a team with lists of pokemon """
        leads = lists_of_pokemon[0]
        for pokemon in leads:
            for p in self.team_maker.game_master.get('pokemon'):
                if p.get('speciesId') != pokemon[0]:
                    continue
                pokemon_types = p.get('types')

                weaknesses = set()
                weaknesses_dict = defaultdict(int)
                for t in pokemon_types:
                    for chart_type, chart_effectiveness in self.types.items():
                        weaknesses_dict[chart_type] += chart_effectiveness[t.capitalize()]
                        if chart_effectiveness[t.capitalize()] > 1:
                            weaknesses.add(chart_type.lower())
                weaks = {x:y for x,y in weaknesses_dict.items() if y>2.3}
                print(f"{pokemon[0]} is weak to {weaknesses}")
                print(f"{pokemon[0]} weaknesses: {weaks}")


class MetaTeamDestroyer:
    """
    Creator of teams to destroy the meta
    """
    def __init__(self, rating=None, league="ULP", days_back=None, num_reports=None):
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
        #self.all_pokemon = requests.get("https://vps.gobattlelog.com/data/overall/rankings-2500-premier.json?v=1.23.20").json()
        rankings_url = LEAGUE_RANKINGS.get(league)
        latest_url = LEAGUE_DATA.get(league)
        #self.all_pokemon = requests.get("https://vps.gobattlelog.com/data/overall/rankings-2500-premier.json?v=1.25.10").json()
        self.all_pokemon = requests.get(rankings_url).json()
        self.game_master = requests.get("https://vps.gobattlelog.com/data/gamemaster.json?v=1.25.10").json()
        #latest_url = "https://vps.gobattlelog.com/records/ultra-premier/latest.json?ts=449983.3"
        #latest_url = "https://vps.gobattlelog.com/records/great-retro/latest.json?ts=450211.1"
        #latest_url= "https://vps.gobattlelog.com/records/great/latest.json?ts=450364.2"
        #latest_url= "https://vps.gobattlelog.com/records/great-kanto/latest.json?ts=450364.2"
        self.latest_info = requests.get(latest_url).json().get("records")

        # Sort reports by time and get last X teams
        sorted_latest_info = sorted(self.latest_info, key=lambda x: x.get('time'), reverse=True)
        if num_reports:
            if len(sorted_latest_info) > num_reports - 1:
                self.latest_info = sorted_latest_info[:num_reports]
            else:
                self.latest_info = sorted_latest_info

        # Remove latest by date
        if days_back:
            print(f"Getting last {days_back} days of data")
            self.latest_info = filter(
                lambda record: datetime.fromtimestamp(record.get('time')) > datetime.now() - timedelta(days=days_back),
                self.latest_info
            )
                    

        # Round the rating if one is provided
        if rating:
            rating = int(round(rating/1000., 1)*1000)

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

        # Create a mapping of the counters
        self.species_counters_dict = defaultdict(set)
        self.species_moveset_dict = defaultdict(list)
        for species in self.all_pokemon:
            counters = species.get('counters')
            matchups = species.get('matchups')
            species_id = species.get('speciesId')
            self.species_counters_dict[species_id].update([c.get('opponent') for c in counters])

            # Add the species as counters to the matchups
            for matchup in matchups:
                self.species_counters_dict[matchup.get('opponent')].add(species_id)
        
            # Add the movesets
            self.species_moveset_dict[species.get('speciesId')] = species.get('moveset')

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
        random_pokemons = random.choices(pokemons, weights=weights, k=n)
        return random_pokemons

    def recommend_team(self):
        """
        Returns a team around a random lead mon picked from the anti-meta list.
        After picking a lead, the two back pokemon are chosen as counters to the lead's weaknesses
        """
        print("Choosing a random lead from the leads list")
        lead_counters = self.get_reccommended_counters(self.leads_list)
        random_counter = self.choose_weighted_pokemon(lead_counters)[0]
        self.build_team_from_pokemon(random_counter)
        
    def build_team_from_pokemon(self, pokemon):
        """
        Builds a team with the given pokemon by choosing counbters to it's weaknesses
        """
        print(f"Building a team around {pokemon}")
        lead_weaknesses = self.species_counters_dict[pokemon]
        #print(f"Weaknesses of {pokemon}: {lead_weaknesses}")

        print("Making counters to the lead weaknesses")
        lead_counters_list = [(c, 1) for c in lead_weaknesses]
        counter_counters = self.get_reccommended_counters(lead_counters_list)
        #print(f"counter counters: {counter_counters}")
        #back_pokemons = self.choose_weighted_pokemon(counter_counters, n=2)
        # need to pick one at a time so there are no repeats
        back_pokemon1 = self.choose_weighted_pokemon(counter_counters)[0]
        index = [p[0] for p in counter_counters].index(back_pokemon1)
        counter_counters.pop(index)
        back_pokemon2 = self.choose_weighted_pokemon(counter_counters)[0]

        pokemon_team = [pokemon, back_pokemon1, back_pokemon2]
        
        print(f"Full team:")
        for p in pokemon_team:
            print(f"    {p}: {self.species_moveset_dict[p]}")
        


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
    #creator.create([[('bulbasaur', 1)]])
    #creator.create([[('swampert', 1)]])

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

    #team_maker.uild_team_from_pokemon("hippowdon")
    #for _ in range(10):
        #team_maker.build_team_from_pokemon("seviper")
        #team_maker.build_team_from_pokemon("machamp_shadow")

    return f"Leads\n{lead_counter_text}\nMeta leads\n{lead_text}\n\nSafe swaps\n{ss_counter_text}\nMeta Safe swaps\n{ss_text}\n\nBack\n{back_counter_text}\nMeta back\n{back_text}"


def create_table_from_results(results):
    """
    Creates an html table from the results

    :param results: The results
    :type results: str

    :return: the table for the results
    :rtype: str
    """
    table = ["<html><body style='background-color:lightgreen;'><table border='1' align='center'>"]

    for line in results.split("\n"):
        table.append("<tr>")

        # If a single value in a line then create a new table
        values = line.split("\t")
        if len(values) == 1:
            table.append("</tr></table><br><br><table border='1' align='center' style='background-color:#FFFFE0;'><tr>")
            table.append(f"<td colspan=4 align='center'>{values[0]}</td>")
        else:
            for value in values:
                if value:
                    table.extend(["<td>", value, "</td>"])

        table.append("</tr>")

    table.append("</table></html>")
    return "".join(table)
    

@app.route("/run")
def run():
    league = request.args.get("league", "GL")
    results = get_counters_for_rating(None, league)
    return create_table_from_results(results)
    #return get_counters_for_rating(None, "GL").replace("\t", "&emsp;").replace("\n", "<br>")
    #return "Done!"

if __name__ == "__main__":
    print(get_counters_for_rating(rating=None, league="Remix", days_back=1))
    #app.run(debug=True)
    #print(team_maker.get_moveset_string('bulbasaur', ["TACKLE", "POWER_WHIP", "SLUDGE_BOMB"]))
