"""

 Team generator based on the current meta

 1. Get the most common leads / back lines
 2. Choose lead based on common leads.
 3. Choose back line based on back line
 
 for questions email: aaron@gobattlelog.com
 pvpoke github: https://github.com/pvpoke/pvpoke

 images of pokemon: https://img.pokemondb.net/sprites/black-white/normal/charizard.png

 TODO:
  - [DONE] write gobattlelog data to local DB daily instead of a file
     - Only pull from gobattlelog if/when new data
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
  - [DONE] Fetch data daily instead of every time refreshed and save to DB
  - Flashcard game for move counts
"""

from typing import OrderedDict
import sqlalchemy

import json
import math
import random
import requests
import traceback
from datetime import datetime, date, timedelta
from collections import defaultdict

from application.pokemon.battle_sim import sim_battle
from application.pokemon.leagues import LEAGUES_LIST
from application.utils.database import create_engine, get_simmed_battle, add_simmed_battle, get_all_simmed_battles
from application.utils.utils import CACHE, logger, TableMaker

# The number of pokemon to consider
TOP_TEAM_NUM = None
MIN_COUNTERS = 25
TOP_PERCENT = 1
REQUEST_TIMEOUT = 180
REFRESH_DATA = False
WEIGHT_NUMBERS = False 

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

def set_refresh(refresh):
    """
    Change global refresh to refresh current data
    """
    global REFRESH_DATA
    REFRESH_DATA = refresh


def get_refresh():
    """
    Returns REFRESH_DATA var
    """
    return REFRESH_DATA


def use_weighted_values(value=True):
    """
    Use statistical weights to change the numbers of pokemon
    """
    global WEIGHT_NUMBERS
    WEIGHT_NUMBERS = value


class NoPokemonFound(Exception):
    pass


class PokemonUser:
    """ Pokemon user object """
    def __init__(self, name, password, fav_league, teams, is_admin=False, subscribed=False):
        self.name = name
        self.fav_league = fav_league
        self.teams = teams
        self.password = password
        self.is_admin = is_admin
        self.subscribed = subscribed
    
    def save(self):
        engine = create_engine()
        metadata = sqlalchemy.MetaData()
        table = sqlalchemy.Table("pokemon_user", metadata, autoload=True, autoload_with=engine)
        try:
            # Check if the user exists, then update
            PokemonUser.load(self.name)
            update = table.update().where(table.c.name==self.name).values(
                name=self.name,
                password=self.password,
                fav_league=self.fav_league,
                teams=json.dumps(self.teams),
                is_admin=self.is_admin,
                subscribed=self.subscribed
            )
            engine.execute(update)
        except:
            # else insert
            ins = table.insert().values(
                name=self.name,
                password=self.password,
                fav_league=self.fav_league,
                teams=json.dumps(self.teams),
                is_admin=self.is_admin,
                subscribed=self.subscribed
            )
            engine.execute(ins)
        engine.dispose()

    @classmethod
    def load(self, name):
        # if user doesn't exist then raise exception
        engine = create_engine()
        query_results = engine.execute(f'SELECT * from `pokemon_user` WHERE pokemon_user.name="{name}";')
        if query_results.rowcount == 0:
            raise Exception(f"user '{name}' doesn't exist")
        results = [result for result in query_results][0]
        engine.dispose()
        return PokemonUser(
            name=results[0],
            password=results[1],
            fav_league=results[2],
            teams=json.loads(results[3]),
            is_admin=results[4],
            subscribed=results[5]
        )


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
    def __init__(self, rating=None, league="GL", num_reports=None):
        """
        :param rating: The rating to get the data from (Default: None)
        :type rating: int
        :param league: The league to check (Default: "ULP")
        :type league: str
        :param num_reports: The number of latest reports to check (Default: None)
        :type num_reports: int
        """
        print("------ Initializing the data -------")

        # Initialize all of the data
        self.league_obj = LEAGUES_LIST[league]
        rankings_url = self.league_obj.ranking_url
        latest_url = self.league_obj.data_url
        self.result_data = {}

        # Get the latest-large data
        latest_url = latest_url.replace('latest', 'latest-large')
        self.league = league
        self.league_cp = self.league_obj.league_value
        self.last_fetched = {}

        # Fetch data from db
        self.all_pokemon = self.get_league_data_from_db(f"all_pokemon_{league}", url=rankings_url)
        game_master_url = "https://vps.gobattlelog.com/data/gamemaster.json?v=1.25.10"
        self.game_master = self.get_league_data_from_db("game_master", url=game_master_url)
        info = self.get_league_data_from_db(league, url=latest_url)
        if isinstance(info, str):
            info = json.loads(info)
        self.latest_info = info.get("records")
        self.all_latest_info = info.get("records") # make a copy for stats weights later

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
            print(f"rating: {rating}")

        self.all_ratings = set(record.get('rating') for record in self.latest_info) 
        print(f"\n\n--- all ratings: {self.all_ratings}")
    
        # Filter out values based on date and rating
        #self.filter_data(rating, days_back, league)

        # start calculating the anti-meta pokemon
        #self.setup(rating)
        self.set_counter_data()

    def filter_data(self, rating, days_back_start, days_back_end, league):
        """
        Filter the data based on the rating and days back chosen
        """
        temp_latest_info = []
        if days_back_start or days_back_end or rating:
            #print(f"\n\n!!! rating: {rating} -  all ratings: {self.all_ratings}") 
            if rating and rating not in self.all_ratings:
                raise NoPokemonFound(f"Rating '{rating}' does not exist. Rating options are: {self.all_ratings}")
            for record in self.latest_info:

                if days_back_start:
                    if datetime.fromtimestamp(record.get('time')) < datetime.now() - timedelta(days=days_back_start):
                        continue
                if days_back_end:
                    if datetime.fromtimestamp(record.get('time')) > datetime.now() - timedelta(days=days_back_end):
                        continue
                if rating:
                    if record.get('rating') != rating:
                        continue
                temp_latest_info.append(record)
            #self.latest_info = temp_latest_info

        else:
            temp_latest_info = self.latest_info

        if len(temp_latest_info) == 0:
            print("!!!!")
            raise NoPokemonFound(f"Did not find {league} data last {days_back_end}-{days_back_start} days at {rating or 'all'} rating")
        self.all_latest_info = [record for record in self.latest_info] # make a copy for stats weights later
        self.latest_info = temp_latest_info

    @staticmethod
    def calculate_pokemon_numbers(record_data, rating):
        """
        Calculate number of each pokemon and win rates

        :return: the number of pokemon in lead/ss/back, win rates, and pokemon teams
        """
        leads = defaultdict(int)
        safeswaps = defaultdict(int)
        backs = defaultdict(int)
        pokemon_win_rates = {'lead': defaultdict(list), 'ss': defaultdict(list), 'back': defaultdict(list)}
        pokemon_teams = defaultdict(list)
        for record in record_data:
            if rating and record.get("rating") != rating:
                continue
            team = record.get("oppo_team")
            pokemon = team.split('/')
            opp_lead = pokemon[0].split(':')[0]
            opp_ss = pokemon[1].split(':')[0]
            opp_back = pokemon[2].split(':')[0]
            leads[opp_lead] += 1
            safeswaps[opp_ss] += 1
            backs[opp_back] += 1
            # think about adding in the record['team'] also
            # add in pokemon win rates
            win = record.get('result') == "L"
            pokemon_win_rates['lead'][opp_lead].append(win)
            pokemon_win_rates['ss'][opp_ss].append(win)
            pokemon_win_rates['back'][opp_back].append(win)

            # Record team win
            backline = sorted([opp_ss, opp_back])
            opp_team = [opp_lead, backline[0], backline[1]]
            team_str = '-'.join(opp_team)
            #pokemon_teams[f'{opp_lead}-{opp_ss}-{opp_back}'].append(win)
            if '?' not in opp_team:
                pokemon_teams[team_str].append(win)
        return (
            [leads, safeswaps, backs],
            pokemon_win_rates,
            pokemon_teams
        )

    def setup(self, rating):
        """
        Setup the anti-meta data
        """
        # Create common leads and backlines lists
        pokemon_counts, pokemon_win_rates, pokemon_teams = self.calculate_pokemon_numbers(self.latest_info, rating)
        leads, safeswaps, backs = pokemon_counts

        self.leads_list = sorted(list(leads.items()), key=lambda x: x[1], reverse=True)
        self.safeswaps_list = sorted(list(safeswaps.items()), key=lambda x: x[1], reverse=True)
        self.backs_list = sorted(list(backs.items()), key=lambda x: x[1], reverse=True)

        if WEIGHT_NUMBERS:
            self.leads_list = self.create_real_pokemon_list(self.leads_list, pos='lead')
            self.safeswaps_list = self.create_real_pokemon_list(self.safeswaps_list, pos='ss')
            self.backs_list = self.create_real_pokemon_list(self.backs_list, pos='back')


        # Record pokemon win rates in each position
        self.pokemon_win_rates = {'leads': {}, 'ss': {}, 'back': {}}
        # square the numbers so they have more effects on the outcome
        #self.pokemon_win_rates['leads'] = {p: f'{wins.count(True)**2}/{len(wins)} || {100*wins.count(True)/len(wins):.2f}%' for p, wins in pokemon_win_rates['lead'].items()}
        self.pokemon_win_rates['leads'] = {p: f'{wins.count(True)}/{len(wins)} || {100*wins.count(True)/len(wins):.2f}%' for p, wins in pokemon_win_rates['lead'].items()}
        self.pokemon_win_rates['ss'] = {p: f'{wins.count(True)}/{len(wins)} || {100*wins.count(True)/len(wins):.2f}%' for p, wins in pokemon_win_rates['ss'].items()}
        self.pokemon_win_rates['back'] = {p: f'{wins.count(True)}/{len(wins)} || {100*wins.count(True)/len(wins):.2f}%' for p, wins in pokemon_win_rates['back'].items()}

        # Record top 10 used team win rates
        self.pokemon_teams = OrderedDict()
        sorted_teams = sorted(pokemon_teams.items(), key=lambda x: [len(x[1]), x[1].count(True)], reverse=True) # sort based on # games
        num_teams = min(30, len(sorted_teams))
        num_teams = len(sorted_teams)
        for team, wins in sorted_teams[:num_teams]:
            self.pokemon_teams[team] = f'{wins.count(True)}/{len(wins)} || {100*wins.count(True)/len(wins):.2f}%'

        # Remove pokemon not in the top TOP_PERCENT from the leads
        if TOP_PERCENT:
            self.leads_list = self.filter_top_pokemon(self.leads_list)
            self.safeswaps_list = self.filter_top_pokemon(self.safeswaps_list)
            self.backs_list = self.filter_top_pokemon(self.backs_list)
        
    def set_counter_data(self):
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

    def get_league_data_from_db(self, league, url=None):
        """
        Returns the league data from the db
        """
        global REFRESH_DATA
        logger.info(f"refresh data: {REFRESH_DATA}")
    
        fetch_new = False
        # first check if in db and if data is older than today
        engine = create_engine()
        metadata = sqlalchemy.MetaData()
        table = sqlalchemy.Table("pokemon_data", metadata, autoload=True, autoload_with=engine)
        query_results = engine.execute(f'SELECT * from `pokemon_data` WHERE pokemon_data.league="{league}";')
        results = [result for result in query_results]
        
        # then check if data is old
        latest_info, last_fetched_date = "{}", None
        if results:
            league_data = results[0]
            last_fetched_date = league_data[2]
            logger.info(f'{league} data was last fetched: {last_fetched_date}')
            logger.info(type(league_data[1]))
            latest_info = json.loads(league_data[1])

            same_date = True
            if type(last_fetched_date) == date:
                same_date = last_fetched_date == datetime.today().date()
            elif type(last_fetched_date) == datetime:
                same_date = last_fetched_date.date() == datetime.today().date()
            if not REFRESH_DATA and same_date:
                self.last_fetched[league] = last_fetched_date
                logger.info(f"Using data refreshed at: {self.last_fetched}")
                logger.info(type(latest_info))
                return json.loads(latest_info) if type(latest_info) == str else latest_info
        else:
            ins = table.insert().values(
                league=league,
                data=json.dumps({}),
                last_fetched_date=datetime.today().date()
            )
            engine.execute(ins)
        # if not in db or old data then pull data and push to db
        if not url:
            league_data = LEAGUES_LIST[league]
            latest_url = league_data.data_url or ""

            # Get the latest-large data
            latest_url = latest_url.replace('latest', 'latest-large')
            url = latest_url

        # Set refresh back to False
        #  because at this point we know we have to refresh
        set_refresh(False)
        logger.info("Getting new data")

        try:
            latest_info = requests.get(url, timeout=REQUEST_TIMEOUT).json()
            json.dump(latest_info, open(f"data/latest_{league}.json", 'w'))
        except Exception as exc:
            print(f"Failed to load latest {league} data because: {exc}")
            try:
                latest_info = json.load(open(f"data/latest_{league}.json"))
            except FileNotFoundError:
                print(f"Failed to find data/latest_{league}.json file. Using stale data from {last_fetched_date}")
                return json.loads(latest_info)

        current_date = datetime.now()
        self.last_fetched[league] = current_date
        update = table.update().where(table.c.league==league).values(
            league=league,
            data=json.dumps(latest_info),
            #last_fetched_date=current_date.date()
            last_fetched_date=current_date
        )
        try:
            engine.execute(update)
        except:
            print(f"Failed to update latest info for: {league}")
        return latest_info

    def get_regionals_data(self, teams):
        """
        Returns recommended regionals team based on two regionals teams

        for now it just returns which pokemon each pokemon beats from the other team
        """
        tc = TeamCreater(self)
        team1, team2 = list(teams.values())[:2]
        # check team 1 against team 2
        #  data = {'first_mon': 5, ...} (1st mon beats 5 pokemon)
        data1 = {p: set() for p in team1}
        data2 = {p: set() for p in team2}

        battles = ["_".join(sorted([p1, p2])) for p1 in team1 for p2 in team2]
        all_battles = get_all_simmed_battles()
        unsimmed_battles = set(battles).difference(set(all_battles.keys()))
        print(f"The following are not simmed yet: {unsimmed_battles}. {len(battles)} - {len(all_battles)}")

        for p1 in set(team1):
            # Get pokemon that beat the given pokemon
            for p2 in set(team2):
                battle = "_".join(sorted([p1, p2]))
                winner = ""
                if battle in all_battles:
                    simmed_battle = all_battles[battle]
                    winner = simmed_battle.get('winner')
                else:
                    winner, health, text = sim_battle(p1, p2, tc)
                    add_simmed_battle(p1, p2, text, winner, health, update=False)
                    all_battles[battle] = {"winner": winner}
    
                if winner == p1:
                    data1[p1].add(p2)
                elif winner == p2:
                    data2[p2].add(p1)
    
        # team 2
        for p2 in set(team2):
            # Get pokemon that beat the given pokemon
            for p1 in set(team1):
                battle = "_".join(sorted([p1, p2]))
                winner = ""
                if battle in all_battles:
                    simmed_battle = all_battles[battle]
                    winner = simmed_battle.get('winner')
                else:
                    winner, health, text = sim_battle(p1, p2, tc)
                    add_simmed_battle(p1, p2, text, winner, health, update=False)
                
                if winner == p2:
                    data2[p2].add(p1)
                elif winner == p1:
                    data1[p1].add(p2)

        data1 = {p: list(v) for p, v in data1.items()}
        data2 = {p: list(v) for p, v in data2.items()}
        return {'1': data1, '2': data2}

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
        league_value = LEAGUES_LIST[league].league_value or '1500'
        league_cp = league_value.split('-')[0]
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

    def create_real_pokemon_list(self, pokemon_list, pos='lead'):
        """
        Create the real list of pokemon by weighting the current number of each pokemon
        by the total number of each pokemon from the ENTIRE population

        https://www.thedataschool.co.uk/henry-mak/how-to-weight-survey-data

        i.e. N(3 days) = 5, N(all time) = 900 -> N(weighted) = 9

        :param pokemon_list: a list of pokemon and # reported. i.e. [('p1', #_) ...]
        :type pokemon_list: list

        :return: New list of same pokemon with new # reported
        """
        # Get total number of each pokemon all time
        all_pokemon_counts, _, _ = self.calculate_pokemon_numbers(self.all_latest_info, None)
        lead, ss, back = all_pokemon_counts
        all_count = lead if pos == 'lead' else ss if pos == 'ss' else back
        sum_all_count = sum(all_count.values())
        total_in_list = sum([p[1] for p in pokemon_list])
        weighted_list = []
        for pokemon, num in pokemon_list:
            current_percent = num / total_in_list * 100
            if not all_count.get(pokemon):
                continue
            #target_percent = num / all_count[pokemon] * 100
            target_percent = all_count[pokemon]/sum_all_count * 100
            weight = target_percent / current_percent
            new_num = math.ceil(weight * num)
            print(pokemon, f"\n\tbefore: {num} - new: {new_num}\n\tcurrent % of data: {current_percent} - overall % of data: {target_percent} - weighted percent: {weight}")
            #print(pokemon, num, new_num, current_percent, target_percent, weight)
            weighted_list.append((pokemon, new_num))
        weighted_list = sorted(weighted_list, key=lambda x: x[1], reverse=True)
        print(weighted_list)
        return weighted_list

    def get_reccommended_counters(self, pokemon_list, exponent=2):
        """ 
        Returns recommended counters to the list of pokemon

         Get the counters in the form of
          [('p1', #,), ('p2', #), ...]
         sorted by #
        """
        # Only focus on top leads
        if TOP_TEAM_NUM:
            pokemon_list = pokemon_list[:TOP_TEAM_NUM]

        # Get counters to the common leads
        # pokemon_list = [('mon1', # of times reported) ...]
        # counter_leads = [['mon1', 'mon2' ..], ...]
        counter_leads = []
        total_reported_pokemon = 0
        recommended_mons = defaultdict(int)
        total_squared_mons = 0
        #pokemon_list = self.create_real_pokemon_list(pokemon_list)
        for lead in pokemon_list:
            #counters = list(self.get_counters(lead[0]))
            
            #counters = self.get_counters(lead[0])
            #counters = list(self.get_counters(lead[0])) * (lead[1] ** 2)
            counters_to_pokemon = list(self.get_counters(lead[0]))

            '''
            counters = counters_to_pokemon * lead[1]
            #counters = list(self.get_counters(lead[0])) * lead[1]
            counter_leads.append(counters)

            # Square value to give them more weight if higher number
            #total_reported_pokemon += lead[1] ** 2
            total_reported_pokemon += lead[1] 
            '''

            # squared weights
            total_squared_mons += lead[1]** exponent
            for counter in counters_to_pokemon:
                recommended_mons[counter] += lead[1] ** exponent

        #print("recommended: ", recommended_mons)
        #print(total_squared_mons)
        '''
        # Get the most common pokemon from the counters
        counter_counts = defaultdict(int)
        for counters in counter_leads:
            for counter in counters:
                counter_counts[counter] += 1
        '''
                

        # Convert counts to percents
        #total_squared_mons = sum(count ** 2 for count in counter_counts.values())
        #for count in counter_counts:
        counter_counts = defaultdict(int)
        for count, number_of_recs in recommended_mons.items():
            #counter_counts[count] = 100.*counter_counts[count] / float(len(pokemon_list))
            #counter_counts[count] = 100.*counter_counts[count] / float(total_reported_pokemon)
            #counter_counts[count] = 100.*((counter_counts[count] ** 2) / float(total_squared_mons))
            counter_counts[count] = 100.*(number_of_recs / float(total_squared_mons))
            #print(count, counter_counts[count])

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


    def simulate_battle(self, pokemon1, pokemon2, n_shields=1):
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
        # Skip the team if it has no pokemon
        if pokemon_team == []:
            return "", []
        results = f"Team for {chosen_pokemon}"
        #pvpoke_link = f"https://pvpoke.com/team-builder/all/{LEAGUE_VALUE[self.league]}/{pokemon_team[0]}-m-{team_ivs[0]}%2C{pokemon_team[1]}-m-{team_ivs[1]}%2C{pokemon_team[2]}-m-{team_ivs[2]}"
        cup = self.league_obj.cup_value or "all"
        pvpoke_link = f"https://pvpoke.com/team-builder/{cup}/{self.league_obj.league_value}/{pokemon_team[0]}-m-0-1-2%2C{pokemon_team[1]}-m-0-1-2%2C{pokemon_team[2]}-m-0-1-2"
        results = f"{results} (<a href='{pvpoke_link}' target='_blank'>See team in pvpoke</a>)"
        results = f"{results}\n<b>Pokemon</b>\t<b>Fast Move</b>\t<b>Charge Moves</b>"
        team_ivs = []
        print(f"Full team:")
        for p in pokemon_team:
            print(f"    {p}: {self.species_moveset_dict[p]}")
            moves = self.species_moveset_dict[p]

            # remove underscores from moves
            moves = [move.replace('_', ' ' ) for move in moves]
            if len(moves) == 3:
                moveset_str = f"{moves[0].title()}\t{moves[1].title()}<br>{moves[2].title()}"
            elif len(moves) == 2:
                moveset_str = f"{moves[0].title()}\t{moves[1].title()}"
            results = f"{results}\n{p.title()}\t{moveset_str}"
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

        # return an empty list (handled later) if no counters
        if not counter_counters:
            print(f"Could not find counters for {pokemon}. Returning empty team")
            return self.team_results([], pokemon)
        
        # If lead is a mega/primal then remove megas/primals from counters
        if "_mega" in pokemon.lower() or "_primal" in pokemon.lower():
            counter_counters = [
                c for c in counter_counters
                if ("mega" not in c[0].lower() and "primal" not in c[0].lower())
            ]

        # need to pick one at a time so there are no repeats      
        back_pokemon1 = self.choose_weighted_pokemon(counter_counters)[0]
        index = [p[0] for p in counter_counters].index(back_pokemon1)
        counter_counters.pop(index)

        # Also need to remove pokemon with similar names by checking for the first part of a pokemon name
        pokemon_keyword = back_pokemon1.split('_')[0]
        counter_counters = [c for c in counter_counters if pokemon_keyword not in c]

        # If the second pokemon was a mega/primal then remove megas and primals
        if "_mega" in back_pokemon1.lower() or "_primal" in back_pokemon1.lower():
            counter_counters = [
                c for c in counter_counters
                if ("_mega" not in c[0].lower() and "_primal" not in c[0].lower())
            ]

        # Choose the third pokemon
        if counter_counters:
            back_pokemon2 = self.choose_weighted_pokemon(counter_counters)[0]
        else:
            print("No counters left. Choosing random pokemon")
            bp2 = random.choice(self.all_pokemon)
            back_pokemon2 = bp2.get("speciesId")

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

def get_counters_for_rating(rating, league="ULP", days_back_start=None, days_back_end=None, exponent=2):
    """ Prints the lead, safe swap, and back line counters at the given rating """
    if league not in LEAGUES_LIST.league_names:
        return f"Did not find league '{league}'", None, ""
    error = ""

    team_maker = MetaTeamDestroyer(rating=rating, league=league)
    try:
        team_maker.filter_data(rating, days_back_start, days_back_end, league)
        team_maker.setup(rating)
    except NoPokemonFound as exc:
        team_maker.filter_data(None, None, None, league)
        team_maker.setup(None)
        error = str(exc)

    #creator = TeamCreater(team_maker)
    #creator.get_weaknesses('bulbasaur')
    #creator.get_weaknesses('swampert')

    print(f"---------- Counters at {rating or 'all'} rating---------")
    print("Leads:")
    lead_counters = team_maker.get_reccommended_counters(team_maker.leads_list, exponent=exponent)
    lead_counter_text = pretty_print_counters(lead_counters, MIN_COUNTERS)

    print("\nCurrent Meta Leads:")
    lead_text = pretty_print_counters(team_maker.leads_list, use_percent=False)

    print("-----\nSafe swaps")
    ss_counters = team_maker.get_reccommended_counters(team_maker.safeswaps_list, exponent=exponent)
    ss_counter_text = pretty_print_counters(ss_counters, MIN_COUNTERS)


    print("\nCurrent Meta SS:")
    ss_text = pretty_print_counters(team_maker.safeswaps_list, use_percent=False)
    
    print("-----\nBack:")
    back_counters = team_maker.get_reccommended_counters(team_maker.backs_list, exponent=exponent)
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
    return f"Recommended Leads\n{lead_counter_text}\nMeta leads\n{lead_text}\n\nRecommended Safe swaps\n{ss_counter_text}\nMeta Safe swaps\n{ss_text}\n\nRecommended Back\n{back_counter_text}\nMeta back\n{back_text}", team_maker, error



def create_table_from_results(results, pokemon=None, width=None, tc=None, tooltip=True):
    """
    Creates an html table from the results.
    Results are in the form:
    value
    value    value    value    value
    value    value    value    value
    value    value    value    value

    :param results: The results
    :type results: str
    :param pokemon: The pokemon to simulatem battles for (Default: None)
    :type pokemon: str

    :return: the table for the results
    :rtype: str
    """
    table = TableMaker(border=1, align="center", bgcolor="#FFFFFF", width=width, pokemon=pokemon)

    for line in results.split("\n"):
        if not line:
            continue
        table.new_row()

        # If a single value in a line then create a new table
        values = line.split("\t")
        if len(values) == 0:
            table.end_row()
            table.end_table()
        elif len(values) == 1:
            table.reset_table()
            table.add_cell(values[0], colspan=4, align="center")
        else:
            for value in values:
                if value:
                    # Provide links to battles
                    if pokemon and ':' in value:
                        league_val = LEAGUES_LIST[CACHE.get('league', '')] or '1500'
                        #league_val = LEAGUE_VALUE.get(CACHE.get('league', ''), '1500')
                        cell_pokemon = value.split(':')[0].strip()

                        # make pvpoke link
                        pvpoke_link = f"https://pvpoke.com/battle/{league_val}/{cell_pokemon}/{pokemon}/11"

                        # simulate battle for text color
                        try:
                            winner, leftover_health, battle_text = sim_battle(cell_pokemon, pokemon, tc)
                            tool_tip_text = "&#013;&#010;</br>".join(battle_text)
                            #logger.info(f"winner: {winner} - leftover_health: {leftover_health}")
                        except Exception as exc:
                            winner = None
                            logger.error(f"{cell_pokemon}")
                            logger.error(traceback.format_exc())
                            leftover_health = 0
                            tool_tip_text=  ""
    
                        if winner == pokemon:
                            text_color = "#00FF00"
                            text_color = "#%02x%02x%02x" % (0, 100 + int(155 * leftover_health), 0)
                        elif winner == cell_pokemon:
                            text_color = "#FF0000"
                            text_color = "#%02x%02x%02x" % (100 + int(155 * leftover_health), 0, 0)
                        else:
                            text_color = "#000000"
                        #logger.info(f"{cell_pokemon}: {text_color}")
                        tooltip_addition = f"<span class='tooltiptext'>{tool_tip_text}</span>" if tooltip else ""
                        value = f"<a class='tooltip1' href='{pvpoke_link}' style='color: {text_color}; text-decoration: none;' target='_blank'>{value}{tooltip_addition}</a>"
                    table.add_cell(value)

        table.end_row()

    table.end_table()
    return table.render()


def get_recent_league():
    """
    Return the league with the most recent data
    """
    engine = create_engine()
    all_rankings = []

    # make a single query for all leagues 
    sql_query = 'SELECT * from `pokemon_data`;'
    query_results = engine.execute(sql_query)
    results = [result for result in query_results]
    leagues = {}
    for result in results:
        # Skip rankings and only get league records
        league = result[0]
        if league.startswith('all_pokemon') or league == "game_master":
            continue
        try:
            records = sorted(json.loads(json.loads(result[1])).get('records'), key=lambda x: x.get('time'), reverse=True)
        except:
            print(f"ERROR: failed to get data for {league}")
            continue
        latest_record = records[0]
        leagues[league] = latest_record.get('time')
    latest_league = sorted(leagues.items(), key=lambda x: x[1], reverse=True)[0]
    print(f"Latest league: {latest_league}")
    return latest_league[0]



if __name__ == "__main__":
    results, team_maker, error = get_counters_for_rating(rating=None, league="MLC", days_back_start=1)
    print(results)

    #print(team_maker.build_team_from_pokemon("zapdos_shadow"))
    #for _ in range(10):
        #team_maker.build_team_from_pokemon("seviper")
        #team_maker.build_team_from_pokemon("machamp_shadow")

    safeswap_team = team_maker.build_safeswap_team("groudon")
    print(safeswap_team)
