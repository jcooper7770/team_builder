"""
 All of the leagues

 TODO:
 - Deprecate "Classic" cups
 - Deprecate cups not coming back
 - Maybe have a 'deprecated' field?
"""

import requests

class League:
    """
    All data on a league/cup
    """
    def __init__(self, name, ranking_url_value, data_url_value, cup_value=None):
        self.name = name
        self.ranking_url = f"https://vps.gobattlelog.com/data/overall/rankings-{ranking_url_value}.json?v=1.28.0"
        self.data_url = f"https://vps.gobattlelog.com/records/{data_url_value}/latest.json?ts=451466.3"
        self.league_value = f"{ranking_url_value}{'-40' if 'classic' in ranking_url_value else ''}"
        self.cup_value = cup_value or name.lower()


class LeagueList:
    """
    A list of leagues/cups
    """
    def __init__(self, leagues):
        self.leagues = {league.name: league for league in leagues}
    
    def __getitem__(self, name):
        return self.leagues.get(name)

    def to_json(self):
        return [
            league.__dict__ for name, league in self.leagues.items()
        ]

    @property
    def league_names(self):
        return self.leagues.keys()

    def get_cup_value(self, league):
        return self.leagues.get(league).cup_value if league in self.leagues else "all"

    @property
    def league_groups(self):
        league_mapping = {"500": "Little Cup", "1500": "Great League", "2500": "Ultra League", "10000": "Master League"}
        result = {x: [] for x in league_mapping.values()}
        for name, league in self.leagues.items():
            ranking_val = league.league_value
            found = False
            for key, value in league_mapping.items():
                if ranking_val.startswith(key):
                    result[value].append((name, league.__dict__))
                    found = True
                    break
            if not found:
                result["Great League"].append((name, league.__dict__))
        # create list of [league, cups, CP value] pairs and sort by CP value
        result2 = []
        reverse_league_mapping = {y: x for x, y in league_mapping.items()}
        for key, value in result.items():
            result2.append([key, value, reverse_league_mapping[key]])
        return sorted(result2, key=lambda x: int(x[2]))

    def add_league(self, name, ranking_url_value, data_url_value):
        if name in self.leagues:
            return False

        new_league =  League(name, ranking_url_value, data_url_value)
        # Test request
        resp = requests.get(new_league.data_url)
        if resp.status_code == 200:
            self.leagues[name] = new_league
            return True
        else:
            return False
    
    def refresh(self):
        leagues = refresh_leagues()
        self.leagues = {name: league for name, league in leagues.leagues.items()}
    
def refresh_leagues():
    return LeagueList([
        # Little cups
        League("Little", "500-little.json", "little"),
        League("Element", "500-element", "element"),
        League("ElementRemix", "500-elementremix", "elementremix"),
        League("Jungle", "500-littlejungle", "littlejungle", cup_value="littlejungle"),
        League("LittleHoliday", "500-littleholiday", "littleholiday", cup_value="littleholiday"),

        # Great cups
        League("GL", "1500", "great"),
        League("Remix", "1500-remix", "great-remix"),
        League("Retro", "1500-retro", "great-retro"),
        League("Holiday", "1500-holiday", "great-holiday"),
        League("Kanto", "1500-kanto", "great-kanto"),
        League("Johto", "1500-johto", "great-johto"),
        League("Hoenn", "1500-hoenn", "great-hoenn"),
        League("Sinnoh", "1500-sinnoh", "great-sinnoh"),
        League("Hisui", "1500-hisui", "great-hisui"),
        League("Love", "1500-love", "great-love"),
        League("Flying", "1500-flying", "great-flying"),
        League("GoFestCatchCup", "1500", "great-catch0622"),
        League("Fossil", "1500-fossil", "great-fossil"),
        League("Summer", "1500-summer", "great-summer"),
        League("Fighting", "1500-fighting", "great-fighting"),
        League("Evolution", "1500-evolution", "great-evolution"),
        League("Willpower", "1500-willpower", "great-willpower"),
        League("Halloween", "1500-halloween", "great-halloween"),
        League("Weather", "1500-weather", "great-weather"),
        League("Electric", "1500-electric", "great-electric"),
        League("Psychic", "1500-psychic", "great-psychic"),
        League("Mountain", "1500-mountain", "great-mountain"),
        League("Spring", "1500-spring", "great-spring"),
        League("Sunshine", "1500-sunshine", "great-sunshine"),
        League("GLSingleType", "1500-single", "great-single"),
        League("Fantasy", "1500-fantasy", "great-fantasy"),
        League("GLCatchS12", "1500", "great-catch1124"),
        League("GLCatchS16", "1500", "great-catch1123"),
        League("GLCatchS17", "1500", "great-catch0224"),

        # Ultra cups
        League("UL", "2500", "ultra"),
        League("ULP", "2500-premier", "ultra-premier"),
        League("ULPC", "2500-premierclassic", "ultra-premierclassic", cup_value="premierclassic"),
        League("ULRemix", "2500-remix", "ultra-remix", cup_value="remix"),
        League("ULHalloween", "2500-halloween", "ultra-halloween"),
        League("ULHoliday", "2500-holiday", "ultra-holiday"),
        League("ULWeather", "2500-weather", "ultra-weather"),
        League("ULSummer", "2500-summer", "ultra-summer"),
        League("ULFantasy", "2500-fantasy", "ultra-fantasy"),

        # Master cups
        League("ML", "10000", "master"),
        League("MLC", "10000-classic", "master", cup_value="classic"),
        League("MLPC", "10000-premierclassic", "master-premierclassic", cup_value="premierclassic"),
        League("MLP", "10000-premier", "master-premier", cup_value="premier"),
        League("MLMega", "10000-mega", "master-mega"),
    ])

LEAGUES_LIST = refresh_leagues()