"""
Flask application

Endpoints:
  - /[?league=GL|Remix|UL|ULP|ULRemix|ML|MLC&pokemon=pokemon]
"""

from flask import Flask, request, render_template

from team_building import get_counters_for_rating, LEAGUE_RANKINGS, NoPokemonFound, LEAGUE_VALUE

app = Flask(__name__, static_url_path="", static_folder="static")

CACHE = {'results': {}, 'team_maker': {}, 'num_days': 1, 'rating': None}
N_TEAMS = 3


class TableMaker:
    """
    Makes a table from results
    """
    def __init__(self, border, align="center", bgcolor="#FFFFFF", width=None):
        self.border = border
        self.align = align
        self.bgcolor = bgcolor
        self.table = []
        self.width = width
        self.first_table = True
        self.new_table()

    def new_table(self):
        options = [
            f"border='{self.border}'",
            f"align='{self.align}'",
            f"style='background-color:{self.bgcolor};'"
        ]
        if self.width:
            options.append(f"width='{self.width}'")
        options_str = " ".join(options)
        self.table.append(f"<table {options_str}>")

    def end_table(self):
        self.table.append("</table>")

    def new_row(self):
        self.table.append("<tr>")

    def end_row(self):
        self.table.append("</tr>")

    def new_line(self):
        self.table.append("<br>")

    def new_header(self, value, colspan):
        self.table.append(f"<th colspan={colspan}>{value}</th>")

    def reset_table(self):
        if not self.first_table:
            self.end_row()
            self.end_table()
            self.new_line()
            self.new_table()
            self.new_row()
        self.first_table = False

    def add_cell(self, value, colspan=None, align=None):
        colspan_text = f" colspan={colspan}" if colspan else ""
        align_text = f" align='{align}'" if align else ""
        self.table.append(f"<td{colspan_text}{align_text}>{value}</td>")

    def render(self):
        return "".join(self.table)

def create_table_from_results(results, pokemon=None, width=None):
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
    table = TableMaker(border=1, align="center", bgcolor="#FFFFFF", width=width)

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
                        league_val = LEAGUE_VALUE.get(CACHE.get('league', ''), '1500')
                        pvpoke_link = f"https://pvpoke.com/battle/{league_val}/{value.split(':')[0].strip()}/{pokemon}/11"
                        value = f"<a href='{pvpoke_link}' style='color: #000000; text-decoration: none;' target='_blank'>{value}</a>"
                    table.add_cell(value)

        table.end_row()

    table.end_table()
    return table.render()


def get_new_data(league, num_days, rating):
    diff_league = CACHE.get("results", {}).get(league) is None
    diff_days = CACHE.get("num_days") != num_days
    diff_rating = CACHE.get("rating") != rating
    return diff_league or diff_days or diff_rating


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/")
def run():
    global CACHE
    global N_TEAMS
    chosen_league = request.args.get("league", "GL")
    chosen_pokemon = request.args.get('pokemon', '')
    num_days = int(request.args.get('num_days', '1'))
    rating = eval(request.args.get('rating', "None"))
    N_TEAMS = int(request.args.get('num_teams', N_TEAMS))
    html = []

    html.append("<h1 align='center'><u>Options</u></h1>")
    # Data tables from cache
    if get_new_data(chosen_league, num_days, rating):
        try:
            results, team_maker = get_counters_for_rating(rating, chosen_league, days_back=num_days)
        except NoPokemonFound as exc:
            error = f"ERROR: Could not get data because: {str(exc)}. Using all data instead"
            html.append(f"<p  style='background-color:yellow;text-align:center'><b>{error}</b></p>")
            results, team_maker = get_counters_for_rating(None, chosen_league, days_back=None)
    else:
        results, team_maker, num_days, rating = CACHE.get('results').get(chosen_league), CACHE.get('team_maker').get(chosen_league), CACHE.get("num_days"), CACHE.get("rating")
    CACHE['results'][chosen_league] = results
    CACHE['team_maker'][chosen_league] = team_maker
    CACHE['num_days'] = num_days
    CACHE['rating'] = rating
    CACHE['league'] = chosen_league

    # Navigation table
    leagues_table = TableMaker(border=1, align="center", bgcolor="#FFFFFF")
    leagues_table.new_header(value="Different Leagues", colspan=len(LEAGUE_RANKINGS))
    leagues_table.new_row()
    for league in sorted(list(LEAGUE_RANKINGS.keys())):
        if league == chosen_league:
            leagues_table.add_cell(league)
        else:
            leagues_table.add_cell(f'<a href="?league={league}&pokemon={chosen_pokemon}&num_days={num_days}">{league}</a>')
    leagues_table.end_row()
    leagues_table.end_table()
    html.append(leagues_table.render())

    # Options: pokemon team, # days of data
    options_table = TableMaker(border=1, align="center")
    options_table.new_header("Options", colspan=2)
    options_table.new_row()
    options_table.add_cell("Create team from pokemon:")
    pokemon_form = []
    pokemon_form.append(f"<input type='hidden' value='{chosen_league}' name='league' />")
    pokemon_form.append(f"<select id='mySelect' name='pokemon'>")
    pokemon_form.append("<option value=''>None</option>")
    for species in sorted(team_maker.all_pokemon, key=lambda x: x.get('speciesId')):
        species_name = species.get('speciesId')
        if species_name == chosen_pokemon:
            pokemon_form.append(f"<option value='{species_name}' selected>{species_name}</option>")
        else:
            pokemon_form.append(f"<option value='{species_name}'>{species_name}</option>")
    pokemon_form.append("</select>")
    options_table.add_cell("".join(pokemon_form))
    options_table.end_row()
    options_table.new_row()
    options_table.add_cell("Number of days of data:")
    options_table.add_cell(f"<input type='text' value={num_days} name=num_days />")
    options_table.end_row()
    options_table.new_row()
    options_table.add_cell("Rating:")
    options_table.add_cell(f"<input type='text' value={rating} name=rating />")
    options_table.end_row()
    options_table.new_row()
    options_table.add_cell("Number of recommended teams:")
    options_table.add_cell(f"<input type='text' value={N_TEAMS} name=num_teams />")
    options_table.end_row()
    options_table.new_row()
    options_table.add_cell("<input type='submit' value='submit' /></p></form>", colspan=2, align="right")
    options_table.end_row()
    options_table.end_table()
    html.extend(["<form action='/'>", options_table.render(), "</form>"])

    if chosen_pokemon:
        try:
            all_team_results = []
            for _ in range(N_TEAMS):
                team_results = team_maker.build_team_from_pokemon(chosen_pokemon)
                all_team_results.append(team_results)
            team_results = "\n".join(all_team_results)
        except:
            team_results = f"Could not create team for {chosen_pokemon} in {chosen_league}"
    else:
        html.append("<h1 align='center'><u>Recommended Teams</u></h1>")
        team_results = ""
        for _ in range(N_TEAMS):
            team_results=f"{team_results}\n{team_maker.recommend_team()}"
    html.append(create_table_from_results(team_results, width='50%'))

    html.append("<h1 align='center'><u>Meta Data</u></h1>")
    html.append("<div align='center'><button onclick='hideData()'>Toggle data</button></div>")
    html.append("<div id='data'>")
    html.append(create_table_from_results(results, pokemon=chosen_pokemon, width='75%'))
    html.append("</div>")

    #html.append("</body></html>")
    #return "".join(html)
    return render_template("index.html", body="".join(html))

    
if __name__ == "__main__":
    app.run(debug=True)
