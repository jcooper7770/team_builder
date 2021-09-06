"""
Flask application

Endpoints:
  - /run[?league='GL|Remix|UL|ULP|ULRemix|ML|MLC']
"""

from flask import Flask, request, url_for

from team_building import get_counters_for_rating, LEAGUE_RANKINGS

app = Flask(__name__, static_url_path="/static")


class TableMaker:
    """
    Makes a table from results
    """
    def __init__(self, border, align="center", bgcolor="#FFFFE0"):
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
    table = TableMaker(border=1, align="center", bgcolor="#FFFFE0")

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


@app.route("/run")
def run():
    chosen_league = request.args.get("league", "GL")
    chosen_pokemon = request.args.get('pokemon', '')
    html = ["<html><body style='background-color:lightblue;'>"]

    # Header
    html.append('<h1 style="text-align:center;">Anti-Meta Team Generator</h1>')
    html.append('<p style="text-align:center;"><img src="/static/flippinCoopLogo.png" width=500 height=500></p>')

    # Navigation table
    leagues_table = TableMaker(border=1, align="center", bgcolor="#FFFFFF")
    leagues_table.new_header(value="Different Leagues", colspan=len(LEAGUE_RANKINGS))
    leagues_table.new_row()
    for league in sorted(list(LEAGUE_RANKINGS.keys())):
        if league == chosen_league:
            leagues_table.add_cell(league)
        else:
            leagues_table.add_cell(f'<a href="/run?league={league}&pokemon={chosen_pokemon}">{league}</a>')
    leagues_table.end_row()
    leagues_table.end_table()
    html.append(leagues_table.render())

    # Input pokemon for team
    html.append("<br><br>")
    html.append(f"<form action='/run'><input type='hidden' value='{chosen_league}' name='league' />")
    html.append(f"<p style='text-align:center;'>Pokemon: <input type='text' name='pokemon' value='{chosen_pokemon}'/>")
    html.append("<input type='submit' value='submit' /></p></form>")
    
    # Data tables
    results, team_maker = get_counters_for_rating(None, chosen_league)
    if chosen_pokemon:
        team_results = team_maker.build_team_from_pokemon(chosen_pokemon)
        html.append(create_table_from_results(team_results))
    html.append(create_table_from_results(results))
    html.append("</body></html>")
    return "".join(html)

    
if __name__ == "__main__":
    app.run(debug=True)
