'''
 $ python -m application.pokemon.regionals
'''
import re
import statistics

from application.pokemon.team_building import MetaTeamDestroyer, set_refresh


class Pokemon:
    def __init__(self, species, types):
        self.species = species
        self.types = types
        self.rating = None
    
    def set_rating(self, rating):
        self.rating = rating
    
    def __str__(self):
        rating = f"{self.rating:.3f}" if self.rating is not None else "<unrated>"
        return f"{self.species} [{rating}]"
    
    def __repr__(self):
        return str(self)


class Team:
    def __init__(self, pokemon):
        self.pokemon = pokemon

    def __str__(self):
        return str(sorted(self.pokemon))

    def __repr__(self):
        return str(self)
    
    def __iter__(self):
        return iter(self.pokemon)


def get_teams():
    """
    Gets the teams from the data
    """
    teams = []
    with open("data/latest_Regionals.txt", 'r') as regionals_file:
        for team_line in regionals_file.readlines():
            # Split team
            split_str = '\t' if '\t' in team_line else ' '
            team = team_line.strip().split(split_str)
            team = [pokemon.lower() for pokemon in team]

            # rename pokemon for different forms
            new_team = []
            regex = r"([A-Za-z ']+)( \[([A-Za-z \[\]]*)\])?"
            for pokemon in team:
                name = ""
                matches = re.findall(regex, pokemon)
                #print(pokemon, matches)
                
                # length of 3 means it has a form
                if len(matches) != 3:
                    name = matches[0][0].strip()
                else:
                    # else its normal form
                    name = matches[0][0].strip()
                    form = matches[2][0]
                    if form:
                        name = f"{name}_{form.split()[0]}"
                name = name.replace(' ', '_').replace("'", '')
                #print(name)
                new_team.append(name)

            teams.append(new_team)
            #teams.append(Team(new_team))
    print(teams)
    return teams


def create_optimal_team(team_creator):
    """
    Creates an optimal regionals team

    :return: The optimal team of 6 pokemon
    :rtype: List<str>
    """
    # Get all team data
    regionals_teams = get_teams()

    # Get all pokemon
    all_pokemon = {p['speciesId']:p for p in team_creator.all_pokemon}
    all_pokemon = {p['speciesId']:Pokemon(p['speciesId'], p['types']) for p in team_creator.game_master['pokemon']}
    counters = team_creator.species_counters_dict

    # Get number of times each pokemon wins against each pokemon from each team
    #  { 'p1': 5, 'p2': 6, ...}
    #  { 'p1': [1,4,5], 'p2': [6,3,8], ...}
    #   where [1,4,5] means it beats 1 pokemon on first team, 4 pokemon on 2nd team...
    wins_dict = {p: [] for p in all_pokemon.keys()}
    for optimal_pokemon in all_pokemon.keys():
        for regionals_team in regionals_teams:
            beat_on_team = 0
            for regionals_pokemon in regionals_team:
                counters_to_regional_pokmeon = counters.get(regionals_pokemon, [])
                if optimal_pokemon in counters_to_regional_pokmeon:
                    beat_on_team += 1
            wins_dict[optimal_pokemon].append(beat_on_team)

    # Average
    #avg_wins_dict = {p: sum(v)/len(v) for p, v in wins_dict.items()}

    # Median
    #avg_wins_dict = {p: statistics.median(v) for p, v in wins_dict.items()}

    # Combined
    avg_wins_dict = {p: (statistics.median(v) + statistics.mean(v))/2 for p, v in wins_dict.items()}

    # add pokemon types
    for p, v in avg_wins_dict.items():
        all_pokemon[p].set_rating(v)
        #print(all_pokemon[p])


    # Choose all the top pokemon
    top_wins = sorted(list(avg_wins_dict.items()), key=lambda x: x[1], reverse=True)
    #top_wins = sorted(list(avg_wins_dict.items()), key=lambda x: x[1], reverse=True)
    #print(top_wins)
    top_wins = sorted(list(all_pokemon.values()), key=lambda x: x.rating, reverse=True)
    print([p for p in top_wins if p.rating])
    return top_wins


if __name__ == '__main__':
    set_refresh(False)
    team_creator = MetaTeamDestroyer(league="GL")
    team_creator.set_counter_data()
    create_optimal_team(team_creator)




