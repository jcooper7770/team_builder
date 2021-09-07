"""
Flask application

Endpoints:
  - /run/[?league=GL|Remix|UL|ULP|ULRemix|ML|MLC&pokemon=pokemon]
"""

from flask import Flask, request, render_template

from team_building import get_counters_for_rating, LEAGUE_RANKINGS, NoPokemonFound

app = Flask(__name__, static_url_path="", static_folder="static")

CACHE = {'results': {}, 'team_maker': None, 'num_days': 1, 'rating': None}


class TableMaker:
    """
    Makes a table from results
    """
    def __init__(self, border, align="center", bgcolor="#FFFFFF"):
        self.border = border
        self.align = align
        self.bgcolor = bgcolor
        self.table = []
        self.new_table()

    def new_table(self):
        self.table.append(f"<table border='{self.border}' align='{self.align}' style='background-color:{self.bgcolor};'>")

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
        self.end_row()
        self.end_table()
        self.new_line()
        self.new_table()
        self.new_row()

    def add_cell(self, value, colspan=None, align=None):
        colspan_text = f" colspan={colspan}" if colspan else ""
        align_text = f" align='{align}'" if align else ""
        self.table.append(f"<td{colspan_text}{align_text}>{value}</td>")

    def render(self):
        return "".join(self.table)

def create_table_from_results(results):
    """
    Creates an html table from the results.
    Results are in the form:
    value
    value    value    value    value
    value    value    value    value
    value    value    value    value

    :param results: The results
    :type results: str

    :return: the table for the results
    :rtype: str
    """
    table = TableMaker(border=1, align="center", bgcolor="#FFFFFF")

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
    chosen_league = request.args.get("league", "GL")
    chosen_pokemon = request.args.get('pokemon', '')
    num_days = int(request.args.get('num_days', '1'))
    rating = eval(request.args.get('rating', "None"))
    html = []

    # Data tables from cache
    if get_new_data(chosen_league, num_days, rating):
        try:
            results, team_maker = get_counters_for_rating(rating, chosen_league, days_back=num_days)
        except NoPokemonFound as exc:
            error = f"ERROR: Could not get data because: {str(exc)}. Using all data instead"
            html.append(f"<p  style='background-color:yellow;text-align:center'><b>{error}</b></p>")
            results, team_maker = get_counters_for_rating(None, chosen_league, days_back=None)
    else:
        results, team_maker, num_days, rating = CACHE.get('results').get(chosen_league), CACHE.get('team_maker'), CACHE.get("num_days"), CACHE.get("rating")
    CACHE['results'][chosen_league] = results
    CACHE['team_maker'] = team_maker
    CACHE['num_days'] = num_days
    CACHE['rating'] = rating

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
    options_table.add_cell("<input type='submit' value='submit' /></p></form>", colspan=2, align="right")
    options_table.end_row()
    options_table.end_table()
    html.extend(["<form action='/run/'>", options_table.render(), "</form>"])

    if chosen_pokemon:
        try:
            team_results = team_maker.build_team_from_pokemon(chosen_pokemon)
        except:
            team_results = f"Could not create team for {chosen_pokemon} in {chosen_league}"
        html.append(create_table_from_results(team_results))

    html.append(create_table_from_results(results))

    #html.append("</body></html>")
    #return "".join(html)
    return render_template("index.html", body="".join(html))

    
if __name__ == "__main__":
    app.run(debug=True)
