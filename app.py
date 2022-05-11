"""
Flask application for trampoline logger and pokemon team maker

Endpoints:
  - /[?league=GL|Remix|UL|ULP|ULRemix|ML|MLC&pokemon=pokemon]
  - /logger
  - /logger/landing
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
  - [DONE] Add user profiles
  - Get data from scorsync
  - [DONE] Add in graphs
"""

import datetime
import os
import socket
import traceback
from collections import defaultdict

from flask import Flask, request, render_template, jsonify, redirect, url_for, send_file,\
    session, send_from_directory
from flask_session import Session

from team_building import get_counters_for_rating, LEAGUE_RANKINGS, NoPokemonFound, TeamCreater,\
     create_table_from_results

from trampoline import convert_form_data, get_leaderboards, pretty_print, Practice, current_user, set_current_user,\
     current_event, set_current_event, set_current_athlete,\
     ALL_SKILLS, get_leaderboards, Athlete, get_user_turns, get_turn_dds
from database import create_engine, set_table_name, insert_goal_to_db, get_user_goals, complete_goal,\
    delete_goal_from_db, get_user
from utils import *


app = Flask(__name__, static_url_path="", static_folder="static")
app.config["CACHE_TYPE"] = "null"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#CACHE = {'results': {}, 'team_maker': {}, 'num_days': 1, 'rating': None}
N_TEAMS = 3
USER_GOALS = {
    "bob": [{"goal": "goal1", "done": False}, {"goal": "goal2", "done": True}]
}
LOGGED_IN_USER = ""
SEARCH_DATE = None
ERROR = None


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


@app.route("/logger/delete/<day>/<event>")
def delete_day(day, event):
    """
    Deletes the given day and event
    """
    datetime_to_remove = datetime.datetime.strptime(day, "%m-%d-%Y")
    Practice.delete(datetime_to_remove, event=event)
    return redirect(url_for("trampoline_log"))


@app.route("/logger/search", methods=["POST"])
def search_date():
    """
    Search by certain date
    """
    global SEARCH_DATE
    global ERROR
    ERROR = ""
    practice_date = request.form.get("practice_date")
    if not practice_date:
        SEARCH_DATE = None
    else:
        # convert practice date to datetime
        try:
            SEARCH_DATE = datetime.datetime.strptime(practice_date, "%Y-%m-%d")
        except Exception as error:
            ERROR = error
    return redirect(url_for("trampoline_log"))
    

def _save_trampoline_data(request):
    """
    Saves the routine data from the forms
    """
    # Convert form data to trampoline skills
    form_data = request.form.get('log', '')
    #username = request.form.get('name', None) or current_user()
    username = request.form.get('name', None) or session.get('name')
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
    form_date_str = request.form.get('date', str(datetime.date.today()))
    form_date = datetime.datetime.strptime(form_date_str, "%Y-%m-%d")
    practice = Practice(form_date.date(), routines, event)
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

    # Require user to be logged in to use the app
    if not session.get("name"):
        return redirect(url_for('landing_page'))
    username, event = current_user(), current_event()

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
        #"<h1 style='text-align:center;' class=\"header\">Previous Practices</h1>",
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
        user=session.get('name'),
        goals=get_user_goals(current_user()),
        all_skills=ALL_SKILLS,
        error_text=ERROR
    )


@app.route("/logger/about")
def about_trampoline():
    return render_template("about_trampoline.html", user=session.get("name"))


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
    error_text = ""

    print("----- Refreshed -----")
    # Data tables from cache
    if get_new_data(chosen_league, num_days, rating):
        try:
            results, team_maker = get_counters_for_rating(rating, chosen_league, days_back=num_days)
        except NoPokemonFound as exc:
            error_text = f"ERROR: Could not get data because: {str(exc)}. Using all data instead"
            results, team_maker = get_counters_for_rating(None, chosen_league, days_back=None)
    else:
        results, team_maker, num_days, rating = CACHE.get('results').get(chosen_league), CACHE.get('team_maker').get(chosen_league), CACHE.get("num_days"), CACHE.get("rating")
    CACHE['results'][chosen_league] = results
    CACHE['team_maker'][chosen_league] = team_maker
    CACHE['num_days'] = num_days
    CACHE['rating'] = rating
    CACHE['league'] = chosen_league

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

    return render_template(
        "index.html",
        body="".join(html),
        leagues=sorted(LEAGUE_RANKINGS.keys()),
        current_league=chosen_league,
        all_pokemon=sorted(team_maker.all_pokemon, key=lambda x: x.get('speciesId')),
        chosen_position=chosen_position,
        num_days=num_days,
        rating=rating,
        number_teams=N_TEAMS,
        current_pokemon=chosen_pokemon,
        error_text=error_text
    )


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    """
    Sign up
    """
    if request.method == "POST":
        global ERROR
        ERROR = ""
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        private = True if request.form.get("private")=="true" else False

        if not username:
            ERROR = "Please enter a username"
            return redirect(url_for('sign_up'))
        try:
            get_user(username)
            ERROR = f"Username {username} already exists."
            return redirect(url_for('sign_up'))
        except:
            pass
        '''
        if not password:
            ERROR = "Missing Password"
            return redirect(url_for('sign_up'))
        elif confirm != password:
            ERROR = "Passwords do not match"
            return redirect(url_for('sign_up'))
        '''
        if ERROR:
            return redirect(url_for('sign_up'))
        # Create the user and go to login page
        athlete = Athlete(username, private)
        athlete.save()
        return redirect(url_for('login'))
    return render_template("sign_up.html", error_text=ERROR, user="")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login
    """
    if request.method == "POST":
        global LOGGED_IN_USER
        global ERROR
        ERROR = ""
        username = request.form.get("username", "").lower()
        try:
            get_user(username)
        except:
            ERROR = f"Username {username} does not exists."
            return redirect(url_for('login'))
        session["name"] = username
        if session.get('name'):
            set_current_user(username)
            set_current_athlete(username)
        return redirect(url_for('trampoline_log'))
    return render_template("login.html", user=session.get("name"), error_text=ERROR)


@app.route("/logout", methods=["GET"])
def logout():
    """
    Logout
    """
    global LOGGED_IN_USER
    LOGGED_IN_USER = ""
    session["name"] = None
    return redirect(url_for('login'))


@app.route("/logger/landing")
def landing_page():
    """
    Landing page
    """
    mock_leaderboard = {
        "DD": {
            "Trampoline": {
                "Ruben": 18.2,
                "coop4440": 15.8,
                "Jer": 15.0
            },
            "DMT": {
                "Ruben": 24.1,
                "coop4440": 18.4,
                "Jer": 14.8
            }
        },
        "Flips": {
            "Trampoline": {"Ruben": 10, "Jer": 9},
            "DMT": {"Ruben": 5, "Jer": 2}
        }
    }
    leaderboard = get_leaderboards()
    if not leaderboard["DD"]:
        leaderboard = mock_leaderboard
    return render_template("landing_page.html", user=session.get("name"), leaderboard=leaderboard)


@app.route("/logger/user")
def user_profile():
    """
    User profile
    """
    start_date = request.args.get('chart_start')
    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%m/%d/%Y")
    end_date = request.args.get('chart_end')
    if end_date:
        end_date = datetime.datetime.strptime(end_date, "%m/%d/%Y")

    current_user = session.get('name')
    if not session.get("name"):
        return redirect(url_for('login'))
    # get user from db
    try:
        user_data = get_user(current_user)
    except Exception as exc:
        logger.error(f"Exception: {exc}")
        user_data = {}

    event_turns, _ = get_turn_dds()
    datapts = {}
    day_flips = {
        'trampoline': defaultdict(int),
        'dmt': defaultdict(int),
    }
    flips_per_turn = {
        'trampoline': defaultdict(list),
        'dmt': defaultdict(list)
    }
    turns_per_practice = defaultdict(int)
    for event, all_turns in event_turns.items():
        datapts[f'{event}_dd'] = []
        datapts[f'{event}_flips'] = []
        # TODO: Add in # skills
        for turn in sorted(all_turns, key=lambda x: x['date']):
            # Skip notes
            if turn['turn'].startswith('-'):
                continue
            if current_user and turn['user'].lower() != current_user:
                continue 
            turn_date = str(turn['date']).split()[0]
            if start_date and turn['date'] < start_date:
                continue
            if end_date and turn['date'] > end_date:
                continue
            turn_flips = turn['flips']
            datapts[f'{event}_dd'].append({
                #'x': str(turn['date']).split()[0],
                'x': turn_date,
                'y': turn['dd']
            })
            datapts[f'{event}_flips'].append({
                #'x': str(turn['date']).split()[0],
                'x': turn_date,
                'y': turn_flips
            })
            day_flips[event][turn_date] += turn_flips
            flips_per_turn[event][turn_date].append(turn_flips)
            turns_per_practice[turn_date] += 1
    
    datapts['trampoline_flips_per_day'] = [{'x': date, 'y': flips} for date, flips in sorted(day_flips['trampoline'].items(), key=lambda x: x[0])]
    datapts['dmt_flips_per_day'] = [{'x': date, 'y': flips} for date, flips in day_flips['dmt'].items()]
    datapts['dmt_flips_per_turn'] = [{'x': date, 'y': sum(flips)/len(flips)} for date, flips in flips_per_turn['dmt'].items()]
    datapts['trampoline_flips_per_turn'] = [{'x': date, 'y': sum(flips)/len(flips)} for date, flips in flips_per_turn['trampoline'].items()]
    datapts['turns_per_practice'] = [{'x': date, 'y': turns} for date, turns in sorted(turns_per_practice.items(), key=lambda x: x[0])]

    return render_template(
        "user_profile.html",
        user=current_user,
        user_data=user_data,
        datapts=datapts,
        chart_start=request.args.get('chart_start', ""),
        chart_end=request.args.get('chart_end', "")
    )


@app.route("/logger/user/update", methods=["POST"])
def update_user():
    """
    Update user
    """
    private = True if request.form.get("private")=="true" else False
    compulsory = request.form.get("compulsory")
    optional = request.form.get("optional")
    athlete = Athlete.load(session.get("name"))
    athlete.private = private
    athlete.compulsory = [skill for skill in compulsory.split()]
    athlete.optional = [skill for skill in optional.split()]
    athlete.save()
    return redirect(url_for("user_profile"))


@app.route("/logger/user/export", methods=["GET", "POST"])
def export_user_data():
    """
    Export user data
    """
    if not session.get('name'):
        print(f"User not logged in: {session}")
        return jsonify(status="failure", reason="User not logged in")
    fromDate = request.args.get('from')
    toDate = request.args.get('to')
    user_turns = get_user_turns(session.get("name"), from_date=fromDate, to_date=toDate)
    export_dir = os.path.join(app.root_path, "exported_data")
    #if not os.path.exists("exported_data"):
    if not os.path.exists(export_dir):
        os.mkdir(export_dir)
    
    # Save json file
    #file_path = os.path.join("exported_data", f'{LOGGED_IN_USER}_turns.json')
    #file_path = os.path.join(export_dir, f'{LOGGED_IN_USER}_turns.json')
    #with open(file_path, 'w') as turns_file:
    #    json.dump(user_turns, turns_file, indent=4)
    
    # Save csv file
    #csv_file_path = os.path.join(export_dir, f"{LOGGED_IN_USER}_turns.csv")
    file_name = f"{session.get('name')}_turns.csv"
    #csv_file_path = os.path.join(export_dir, f"{session.get('name')}_turns.csv")
    csv_file_path = os.path.join(export_dir, file_name)
    with open(csv_file_path, 'w') as turns_file:
        turns_file.write("turn number, skills, date, event\n")
        for turn in user_turns:
            turn_date = str(turn[2]).split()[0]
            line = f"{turn[0]}, {turn[1]}, {turn_date}, {turn[4]}\n"
            turns_file.write(line)
    # TODO: figure out how to download the saved csv file, then delete it
    if request.method == "GET":
        return send_file(csv_file_path, as_attachment=True, cache_timeout=0)
        #return send_from_directory(export_dir, file_name, mimetype="text/csv", as_attachment=True)
    return jsonify(status="success", filename=csv_file_path)


@app.route("/logger/chart", methods=["GET"])
def chart():
    event_turns, _ = get_turn_dds()
    current_user = session.get('name')
    datapts = {}
    for event, all_turns in event_turns.items():
        datapts[f'{event}_dd'] = []
        datapts[f'{event}_flips'] = []
        for turn in sorted(all_turns, key=lambda x: x['date']):
            if current_user and turn['user'] != current_user:
                continue 
            datapts[f'{event}_dd'].append({
                'x': str(turn['date']).split()[0],
                'y': turn['dd']
            })
            datapts[f'{event}_flips'].append({
                'x': str(turn['date']).split()[0],
                'y': turn['flips']
            })
    return render_template("graph.html", user=current_user, datapts=datapts)


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