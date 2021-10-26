"""
Flask application

Endpoints:
  - /[?league=GL|Remix|UL|ULP|ULRemix|ML|MLC&pokemon=pokemon]

TODO:
  - Login with username and keep track of list of pokemon the user doesn't have
  - add youtube link to tutorial on about page
  - store team data in a database and refresh once a day
"""

import datetime
import json
import os
import re
import sys
import traceback

from flask import Flask, request, render_template, jsonify, redirect, url_for

from team_building import get_counters_for_rating, LEAGUE_RANKINGS, NoPokemonFound, LEAGUE_VALUE, TeamCreater
from battle_sim import sim_battle
from trampoline import convert_form_data, pretty_print, Practice, current_user, set_current_user,\
     current_event, set_current_event, NON_SKILLS

app = Flask(__name__, static_url_path="", static_folder="static")

CACHE = {'results': {}, 'team_maker': {}, 'num_days': 1, 'rating': None}
N_TEAMS = 3

import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('werkzeug') # grabs underlying WSGI logger
handler = logging.FileHandler('test.log') # creates handler for the log file
logger.addHandler(handler) # adds handler to the werkzeug WSGI logger

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
                        value = f"<a class='tooltip' href='{pvpoke_link}' style='color: {text_color}; text-decoration: none;' target='_blank'>{value}{tooltip_addition}</a>"
                    table.add_cell(value)

        table.end_row()

    table.end_table()
    return table.render()


def make_recommended_teams(team_maker, chosen_pokemon, chosen_league, chosen_position):
    """
    Makes N_TEAMS unique teams
    """
    try:
        all_team_results = []
        chosen_teams = []
        tries = 0
        while len(chosen_teams) < N_TEAMS and tries < 2*N_TEAMS:
            tries += 1
            team_results, pokemon_team = team_maker.recommend_team(chosen_pokemon, position=chosen_position)
            if pokemon_team in chosen_teams:
                continue
            chosen_teams.append(pokemon_team)
            all_team_results.append(team_results)
        team_results = "\n".join(all_team_results)
    except Exception as exc:
        tb = traceback.format_exc()
        team_results = f"Could not create team for {chosen_pokemon} in {chosen_league} because: {exc}.\n{tb}"
    return team_results


def get_new_data(league, num_days, rating):
    diff_league = CACHE.get("results", {}).get(league) is None
    diff_days = CACHE.get("num_days") != num_days
    diff_rating = CACHE.get("rating") != rating
    return diff_league or diff_days or diff_rating


def skills_table(skills, title="Routines"):
    """
    Writes all trampoline skills to a table
    """
    if skills:
        most_cols = max([len(turn.skills) for turn in skills])
    else:
        most_cols = 0
    total_flips = 0
    total_difficulty = 0
    total_skills = 0
    skills_table = TableMaker(border=1, align="center", width="30%")
    skills_table.new_header(title, colspan=most_cols+8)
    for turn_num, turn in enumerate(skills):
        skills_table.new_row()
        # Turn number
        skills_table.add_cell(f"<b>{turn_num+1}</b>")

        # Skills
        for skill in turn.skills:
            skills_table.add_cell(skill.shorthand)
        # metrics
        skills_table.add_cell("")
        for _ in range(most_cols - len(turn.skills)):
            skills_table.add_cell("")

        # total skills
        num_skills = len([skill for skill in turn.skills if skill.shorthand not in NON_SKILLS])
        skills_table.add_cell(num_skills)
        total_skills += num_skills
        skills_table.add_cell(total_skills)

        # total flips
        skills_table.add_cell(turn.total_flips)
        total_flips += turn.total_flips
        skills_table.add_cell(total_flips)

        # total difficulty
        skills_table.add_cell(f"{turn.difficulty:0.1f}")
        total_difficulty += turn.difficulty
        skills_table.add_cell(f"{total_difficulty:0.1f}")

        skills_table.end_row()
    skills_table.end_table()
    return skills_table.render()

@app.route("/logger/_clear")
def clear_history():
    """
    Clears historical data
    """
    if os.path.exists("routines.txt"):
        os.remove("routines.txt")
        logger.info("deleted file!")
        return jsonify(status="success")
    else:
        logger.info("did not delete")
        return jsonify(status="fail")
        

@app.route("/logger/_clearDay")
def clear_day():
    """
    Clears current day's data for the current user
    """
    if Practice.delete(datetime.date.today()):
        logger.info("deleted today's data")
        return jsonify(status="success")
    logger.error("Failed to delete data for today")
    return jsonify(status="fail")


def _save_trampoline_data(request):
    """
    Saves the routine data from the forms
    """
    # Convert form data to trampoline skills
    form_data = request.form.get('log', '')
    username = request.form.get('name', None) or current_user()
    event = request.form.get('event', None) or current_event()
    set_current_event(event)
    set_current_user(username)
    logger.info(f"Username: {username}")
    routines = convert_form_data(form_data, event=event)
    logger.info(request.form.get('log', 'None').split('\r\n'))

    # Save the current practice
    practice = Practice(datetime.date.today(), routines, event)
    saved_practice = practice.save()

    # Log the turns to the log file
    for turn_num, turn in enumerate(routines):
        logger.info(f"{turn_num+1}: {turn.skills}")
    pretty_print(routines, logger.info)

    # Store trampoline skills to a file
    if not os.path.exists('routines.txt'):
        with open('routines.txt','w') as routine_file:
            pass

    # Get the current routines
    with open('routines.txt') as routine_file:
        old_routines = routine_file.read()
    logger.info("-----")
    logger.info(f"old routines: {old_routines}")
    logger.info("-----")

    # Save historical and current routines to routines file
    if form_data:
        with open('routines.txt', 'w') as routine_file:
            new_routines = form_data.replace('\n', '')
            if old_routines:
                routine_file.write('\n'.join([old_routines, new_routines]))
            else:
                routine_file.write(new_routines)



@app.route("/logger", methods=['GET', 'POST'])
def trampoline_log():
    # POST/Redirect/GET to avoid resubmitting form on refresh
    if request.method == "POST":
        _save_trampoline_data(request)
        return redirect(url_for('trampoline_log'))

    username, event = current_user(), current_event()
    if os.path.exists('routines.txt'):
        with open('routines.txt') as routine_file:
            old_routines = routine_file.read()
    else:
        old_routines = ""

    logger.info("-----")
    logger.info(f"old routines: {old_routines}")
    logger.info("-----")

    # Collect all routines up to now
    routines = convert_form_data(old_routines, logger=logger.info)

    # Write all trampoline skills to a table
    table = skills_table(routines)

    # Print out a table per date
    practice_tables = []
    for _, _, practice_files in os.walk(os.path.join("practices", username)):
        for practice_file in sorted(practice_files, reverse=True):
            full_path = os.path.join("practices", username, practice_file)

            # Get the event from the filename
            try:
                practice_event = re.findall("[0-9]{8}_([a-z]*).txt", practice_file)[0]
            except:
                practice_event = ""

            # Load in the practice to get the turns
            with open(full_path) as practice_file:
                practice_data = json.load(practice_file)
                practice = Practice.load(practice_data, practice_event)

            # Add the turns into a table for that practice
            title_date = practice.date.strftime("%A %m/%d/%Y")
            title = f"{title_date} ({practice.event})"
            practice_table = skills_table(practice.turns, title=title)
            practice_tables.append(practice_table)

    all_practice_tables = "<br><br>".join(practice_tables)
            
    html = [
        table,
        "<br><br>",
        "<h1 style='text-align:center;'>Previous Practices</h1>",
        # Div for practices so they are scrollable
        "<div id='practices' class='practices'><br><br>",
        all_practice_tables,
        "</div>"
    ]
    body = "".join(html)
    return render_template("trampoline.html", body=body, username=username, event=event)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/")
def run():
    global CACHE
    global N_TEAMS
    chosen_league = request.args.get("league", "ULPC")
    chosen_pokemon = request.args.get('pokemon', '')
    chosen_position = request.args.get('position', 'lead')
    num_days = int(request.args.get('num_days', '1'))
    rating = eval(request.args.get('rating', "None"))
    use_tooltip = bool(request.args.get('tooltips', False))
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
    leagues_table = TableMaker(border=1, align="center", bgcolor="#FFFFFF", width="30%")
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
    options_table = TableMaker(border=1, align="center", width="30%")
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
    pokemon_form.append(f"<br><input type='radio' id='lead' value='lead' name='position'{' checked' if chosen_position=='lead' else ''}><label for='lead'>In the lead</label>")
    pokemon_form.append(f"<br><input type='radio' id='back' value='back' name='position'{' checked' if chosen_position=='back' else ''} ><label for='back'>In the back</label>")
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

    # Recommended teams
    #  make N_TEAMS unique teams. But try 2*N_TEAMS times to make unique teams
    team_results = make_recommended_teams(team_maker, chosen_pokemon, chosen_league, chosen_position)

    html.append("<h1 align='center'><u>Recommended Teams</u></h1>")
    html.append(create_table_from_results(team_results, width='50%'))

    # Data
    html.append("<h1 align='center'><u>Meta Data</u></h1>")
    html.append("<div align='center'><button onclick='hideData()'>Toggle data</button></div>")
    html.append("<div id='data' class='data'>")
    tc = TeamCreater(team_maker)
    html.append(create_table_from_results(results, pokemon=chosen_pokemon, width='75%', tc=tc, tooltip=use_tooltip))
    html.append("</div>")

    return render_template("index.html", body="".join(html))

    
if __name__ == "__main__":
    app.run(debug=True)
