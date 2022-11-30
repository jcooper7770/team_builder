"""
 All of the leagues
"""

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

    @property
    def league_names(self):
        return self.leagues.keys()

    def get_cup_value(self, league):
        return self.leagues.get(league).cup_value if league in self.leagues else "all"


LEAGUES_LIST = LeagueList([
    # Little cups
    League("Little", "500-little.json", "little"),
    League("Element", "500-element", "element"),
    League("ElementRemix", "500-elementremix", "elementremix"),
    League("Jungle", "500-littlejungle", "littlejungle", cup_value="littlejungle"),

    # Great cups
    League("GL", "1500", "great"),
    League("Remix", "1500-remix", "great-remix"),
    League("Retro", "1500-retro", "great-retro"),
    League("Kanto", "1500-kanto", "great-kanto"),
    League("Holiday", "1500-holiday", "great-holiday"),
    League("Sinnoh", "1500-sinnoh", "great-sinnoh"),
    League("Love", "1500-love", "great-love"),
    League("Johto", "1500-johto", "great-johto"),
    League("Flying", "1500-flying", "great-flying"),
    League("GoFestCatchCup", "1500", "great-catch0622"),
    League("Fossil", "1500-fossil", "great-fossil"),
    League("Hisui", "1500-hisui", "great-hisui"),
    League("Summer", "1500-summer", "great-summer"),
    League("Fighting", "1500-fighting", "great-fighting"),
    League("Evolution", "1500-evolution", "great-evolution"),
    League("Willpower", "1500-willpower", "great-willpower"),
    League("Halloween", "1500-halloween", "great-halloween"),
    League("CatchS12", "1500", "great-catch1124"),

    # Ultra cups
    League("UL", "2500", "ultra"),
    League("ULP", "2500-premier", "ultra-premier"),
    League("ULPC", "2500-premierclassic", "ultra-premierclassic", cup_value="premierclassic"),
    League("ULRemix", "2500-remix", "ultra-remix", cup_value="remix"),
    League("ULHalloween", "2500-halloween", "ultra-halloween"),

    # Master cups
    League("ML", "10000", "master"),
    League("MLC", "10000-classic", "master", cup_value="classic"),
    League("MLPC", "10000-premierclassic", "master-premierclassic", cup_value="premierclassic"),
])
