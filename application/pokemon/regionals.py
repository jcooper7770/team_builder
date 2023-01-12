import re
import statistics

from application.pokemon.team_building import MetaTeamDestroyer, set_refresh


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

    # Choose all the top pokemon
    top_wins = sorted(list(avg_wins_dict.items()), key=lambda x: x[1], reverse=True)
    top_wins = sorted(list(avg_wins_dict.items()), key=lambda x: x[1], reverse=True)
    print(top_wins)
    return top_wins


if __name__ == '__main__':
    set_refresh(False)
    team_creator = MetaTeamDestroyer(league="GL")
    team_creator.set_counter_data()
    create_optimal_team(team_creator)




