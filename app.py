"""
Flask application

Endpoints:
  - /[?league=GL|Remix|UL|ULP|ULRemix|ML|MLC&pokemon=pokemon]
  - /logger
  - /login
  - /logout

TODO:
  - Login with username and keep track of list of pokemon the user doesn't have
  - add youtube link to tutorial on about page
  - [DONE] store team data in a database and refresh once a day
  - Split trampoline code from pokemon code
  - [DONE] (Trampoline) Replace "Routines" section with "Goals" with checkboxes
  - [DONE] (Trampoline) Write goals to DB
  - [DONE] Search for certain day of practice
"""

import datetime
import json
import os
import re
import socket
import sys
import traceback

from flask import Flask, request, render_template, jsonify, redirect, url_for

from team_building import get_counters_for_rating, LEAGUE_RANKINGS, NoPokemonFound, LEAGUE_VALUE, TeamCreater
from battle_sim import sim_battle
from trampoline import convert_form_data, pretty_print, Practice, current_user, set_current_user,\
     current_event, set_current_event, set_current_athlete, NON_SKILLS, SKILLS, POSITIONS, create_engine,\
     get_from_db, delete_from_db, set_table_name, insert_goal_to_db, get_user_goals, complete_goal, delete_goal_from_db
from utils import *

app = Flask(__name__, static_url_path="", static_folder="static")
app.config["CACHE_TYPE"] = "null"

CACHE = {'results': {}, 'team_maker': {}, 'num_days': 1, 'rating': None}
N_TEAMS = 3
USER_GOALS = {
    "bob": [{"goal": "goal1", "done": False}, {"goal": "goal2", "done": True}]
}
LOGGED_IN_USER = ""
SEARCH_DATE = None

import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('werkzeug') # grabs underlying WSGI logger
handler = logging.FileHandler('test.log') # creates handler for the log file
logger.addHandler(handler) # adds handler to the werkzeug WSGI logger


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
    try:
        if Practice.delete(datetime.date.today()):
            logger.info("deleted today's data")
            return jsonify(status="success")
    except Exception as error:
        logger.info(f"Failed to delete because: {error}")
    logger.error("Failed to delete data for today")
    return jsonify(status="fail")


@app.route("/logger/search", methods=["POST"])
def search_date():
    """
    Search by certain date
    """
    global SEARCH_DATE
    practice_date = request.form.get("practice_date")
    if not practice_date:
        SEARCH_DATE = None
    else:
        # convert practice date to datetime
        SEARCH_DATE = datetime.datetime.strptime(practice_date, "%m/%d/%Y")
    return redirect(url_for("trampoline_log"))
    

def _save_trampoline_data(request):
    """
    Saves the routine data from the forms
    """
    # Convert form data to trampoline skills
    form_data = request.form.get('log', '')
    username = request.form.get('name', None) or current_user()
    event = request.form.get('event', None) or current_event()
    notes = request.form.get('notes', None)
    set_current_event(event)
    set_current_user(username)
    set_current_athlete(username)
    logger.info(f"Username: {username}")
    routines = convert_form_data(form_data, event=event, notes=notes)
    logger.info(request.form.get('log', 'None').split('\r\n'))

    # Save new goal
    all_goals = get_user_goals(current_user())
    
    num_goals = request.form.get("goals_form")
    if num_goals:
        # reset all checkboxes
        for goal_num, _ in enumerate(all_goals):
            complete_goal(current_user(), all_goals[goal_num]["goal"], done=False)
            
        goal_string = request.form.get('goal_string', None)
        if goal_string:
            new_goal = {"goal": goal_string, "done": False}
            insert_goal_to_db(current_user(), goal_string)
        for key in request.form.keys():
            if key in ["goal_string", "goals_form"]:
                continue
            if key.startswith("delete"):
                deleted_goal_num = int(key[6:])
                delete_goal_from_db(current_user(), all_goals[deleted_goal_num]["goal"])
                continue
            try:
                # inside of try/except incase checked goal was deleted
                complete_goal(current_user(), all_goals[int(key)]["goal"])
            except:
                pass


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

    # Get data from database
    user_practices = Practice.load_from_db(username, date=SEARCH_DATE)
    for practice in user_practices:
        # Add the turns into a table for that practice
        title_date = practice.date.strftime("%A %m/%d/%Y")
        title = f"{title_date} ({practice.event})"
        practice_table = skills_table(practice.turns, title=title)
        practice_tables.append(practice_table)

    all_practice_tables = "<br><br>".join(practice_tables)
   
    html = [
        "<h1 style='text-align:center;' class=\"header\">Previous Practices</h1>",
        # Div for practices so they are scrollable
        "<div id='practices' class='practices'><br><br>",
        all_practice_tables,
        "</div>"
    ]
    body = "".join(html) if all_practice_tables else ""
    return render_template(
        "trampoline.html",
        body=body, username=username,
        event=event,
        routine_text=request.args.get('routine', ''),
        user=LOGGED_IN_USER,
        goals=get_user_goals(current_user())
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/")
def run():
    global CACHE
    global N_TEAMS
    chosen_league = request.args.get("league", "GL")
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



@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login
    """
    if request.method == "POST":
        global LOGGED_IN_USER
        LOGGED_IN_USER = request.form.get("username")
        if LOGGED_IN_USER:
            set_current_user(LOGGED_IN_USER)
        return redirect(url_for('trampoline_log'))
    return render_template("login.html", user=LOGGED_IN_USER)


@app.route("/logout", methods=["GET"])
def logout():
    """
    Logout
    """
    global LOGGED_IN_USER
    LOGGED_IN_USER = ""
    return redirect(url_for('login'))



def get_app():
    """
    Returns the app
    """
    return app

    
if __name__ == "__main__":
    # Start db connection
    if socket.gethostname().endswith("secureserver.net"):
        set_table_name("data")
        create_engine(table_name="data")
        logger.info("Using main data table")
    else:
        set_table_name("test_data")
        create_engine(table_name="test_data")
        logger.info("Using test data table")

    # start app
    app.run(debug=True)
