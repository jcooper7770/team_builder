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
  - Add graphs to pokemon website
  - Split templates for pokemon and trampoline sites
  - [DONE] Add login for pokemon site
  - Add teams for pokemon users
"""

import datetime
import json
import os
import socket
import subprocess
import traceback
from collections import defaultdict, OrderedDict
from passlib.hash import sha256_crypt

from flask import Flask, request, render_template, jsonify, redirect, url_for, send_file,\
    session, send_from_directory
from flask_session import Session

from application.pokemon.leagues import LEAGUES_LIST
from application.pokemon.team_building import MetaTeamDestroyer, PokemonUser, get_counters_for_rating, NoPokemonFound, TeamCreater,\
     create_table_from_results, set_refresh, get_refresh, use_weighted_values
from application.pokemon.battle_sim import sim_battle
from application.pokemon.move_counts import get_move_counts, make_image, get_all_rankings

from application.trampoline.trampoline import convert_form_data, get_leaderboards, pretty_print, Practice, current_user, set_current_user,\
     current_event, set_current_event, set_current_athlete,\
     ALL_SKILLS, get_leaderboards, Athlete, get_user_turns, get_turn_dds
from application.utils.database import create_engine, get_users_and_turns, set_table_name, insert_goal_to_db, get_user_goals, complete_goal,\
    delete_goal_from_db, get_user, get_simmed_battle, add_simmed_battle, add_airtime_to_db, get_user_airtimes, delete_airtime_from_db
from application.utils.utils import *


app = Flask(__name__, static_url_path="", static_folder="static")
app.config["CACHE_TYPE"] = "null"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
Session(app)

#CACHE = {'results': {}, 'team_maker': {}, 'num_days': 1, 'rating': None}
N_TEAMS = 3
USER_GOALS = {
    "bob": [{"goal": "goal1", "done": False}, {"goal": "goal2", "done": True}]
}
LOGGED_IN_USER = ""
SEARCH_SKILLS = "" # Skills to search for


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


@app.route("/data/refresh", methods=["POST"])
def refresh_pokemon_data():
    """
    Refreshes the league data
    """
    data = request.get_json()
    logger.info(f"\n\n\nRefreshing data for {data}")
    set_refresh(True)
    #return jsonify(status="success")
    return "success"

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


@app.route("/logger/edit/<day>/<event>")
def edit_day(day, event):
    """
    Edits the given day and event
    """
    print(f"Editing {day} and {event}")
    datetime_to_edit = datetime.datetime.strptime(day, "%m-%d-%Y")
    practices = Practice.load_from_db(session.get('name'), datetime_to_edit)
    practice = [p for p in practices if p.event == event]
    raw_log = '\n'.join(p.raw() for p in practice)
    session['log'] = {day: raw_log}
    session["search_date"] = datetime_to_edit
    session['event'] = event
    print(f"log: {raw_log}")
    return redirect(url_for("trampoline_log"))


@app.route("/logger/delete/<day>/<event>")
def delete_day(day, event):
    """
    Deletes the given day and event
    """
    datetime_to_remove = datetime.datetime.strptime(day, "%m-%d-%Y")
    Practice.delete(datetime_to_remove, event=event)
    return redirect(url_for("trampoline_log"))


@app.route("/logger/search/skills", methods=["POST"])
def search_skills():
    """
    Search practices based on a skill or group of skills
    """
    global SEARCH_SKILLS
    skills = request.form.get('practice_skills', '')

    # expand user compulsory or optional
    if skills == "optional":
        user = Athlete.load(session.get('name'))
        skills = user.optional
    if skills == "compulsory":
        user = Athlete.load(session.get('name'))
        skills = user.compulsory
    session["search_skills"] = skills
    #SEARCH_SKILLS = skills
    return redirect(url_for('trampoline_log'))


@app.route("/logger/search", methods=["POST", "GET"])
def search_date():
    """
    Search by certain date
    """
    session["error"] = ""
    if request.method == "GET":
        practice_date = request.args.get("practice_date", "")
    else:
        practice_date = request.form.get("practice_date", "")

    if not practice_date:
        session["search_date"] = None
    else:
        # convert practice date to datetime
        try:
            session["search_date"] = datetime.datetime.strptime(practice_date, "%Y-%m-%d")
        except Exception as error:
            session["error"] = error
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

    # Save airtime
    airtime = request.form.get("airtime_form")
    all_airtimes = get_user_airtimes(current_user())
    if airtime:
        airtime_str = request.form.get('airtime_string')
        try:
            airtime_str = f"{float(airtime_str):.2f}"
        except:
            pass
        # add in date field
        form_date_str = request.form.get('airtime-date', str(datetime.date.today()))
        form_date = datetime.datetime.strptime(form_date_str, "%Y-%m-%d")
        add_airtime_to_db(current_user(), airtime_str, form_date)

        # remove deleted airtimes
        for key in request.form.keys():
            if key in ["airtime_string", "airtime_form"]:
                continue
            if key.startswith("delete"):
                deleted_airtime_num = int(key[6:])
                delete_airtime_from_db(current_user(), all_airtimes[deleted_airtime_num])
                continue
   
    # Save the current practice
    form_date_str = request.form.get('date', str(datetime.date.today()))
    form_date = datetime.datetime.strptime(form_date_str, "%Y-%m-%d")
    session['current_date'] = form_date
    if session.get('search_date') != session.get('current_date'):
        print(f"search: {session.get('search_date')} - current: {session.get('current_date')}")
        session['search_date'] = None
    practice = Practice(form_date.date(), routines, event)
    replace_practice = session.get('log', {}).get(form_date.strftime('%m-%d-%Y')) is not None
    print(f"~~~~~~~~~~~~replace: {replace_practice} - log {session.get('log')} - date {form_date.strftime('%m-%d-%Y')}")
    saved_practice = practice.save(replace=replace_practice)
    session['log'] = {}

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
    #logger.info("-----")
    #logger.info(f"old routines: {old_routines}")
    #logger.info("-----")

    # Save historical and current routines to routines file
    if form_data:
        with open('routines.txt', 'w') as routine_file:
            new_routines = form_data.replace('\n', '')
            if old_routines:
                routine_file.write('\n'.join([old_routines, new_routines]))
            else:
                routine_file.write(new_routines)


@app.route("/logger/coach/home", methods=['GET'])
def coach_home():
    """
    Home for coaches
    """
    coach = Athlete.load(session.get('name'))
    #current_athlete = request.args.get('athlete') or session.get('current_athlete', '')
    current_athlete = request.args.get('athlete')
    session["current_athlete"] = current_athlete

    body = ""
    all_athletes = [current_athlete] if current_athlete else coach.athletes
    print(f"\n\n --- {all_athletes}")
    practice_tables = []
    practices = []
    for athlete in all_athletes:
        # Get data from database
        user_practices = Practice.load_from_db(athlete, date=session.get("search_date"), skills=session.get("search_skills", ""))
        for practice in user_practices:
            practices.append({'athlete': athlete, 'practice': practice})
    
    # sort all practices to show them in order
    practices.sort(key=lambda p: p['practice'].date, reverse=True)

    for practice in practices:
        # Add the turns into a table for that practice
        title_date = practice['practice'].date.strftime("%A %m/%d/%Y")
        title = f"{practice['athlete']}: {title_date} ({practice['practice'].event})"
        practice_table = skills_table(practice['practice'].turns, title=title, expand_comments=False)
        practice_tables.append(practice_table)

    all_practice_tables = "<br><br>".join(practice_tables)

    html = [
        # Div for practices so they are scrollable
        "<div id='practices' class='practices'><br><br>",
        all_practice_tables,
        "</div>"
    ]
    body = "".join(html) if all_practice_tables else ""

    logging.info(f"error: {session.get('error', '')}")

    return render_template(
        "trampoline/coach_home.html",
        body=body,
        athletes=coach.athletes,
        current_athlete=current_athlete,
        user=session.get('name'),
        goals=get_user_goals(current_user()),
        error_text=session.get('error'),
        search_date=session.get("search_date").strftime("%Y-%m-%d") if session.get("search_date") else None,
        search_skills=session.get("search_skills", ""),
        user_turns=[]
    )



@app.route("/logger/<username>/practices", methods=['GET'])
def trampoline_user_practices(username):
    """
    Return user practices
    """
    user = None
    if username == "_current_":
        username = session.get('name')
        return redirect(f"/logger/{username}/practices")

    try:
        user = get_user(username)
    except:
        body = f"User {username} does not exist"
        return render_template("trampoline/user_practices.html", body=body)

    start_date, end_date = (None, None)
    start = request.args.get('start', '') 
    if start:
        try:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
        except:
            body = f"start date '{start}' is not a valid date in form of 'YYYY-mm-dd'"
            return render_template("trampoline/user_practices.html", body=body)
    
    end = request.args.get('end', '')
    if end:
        try:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
        except:
            body = f"end date '{end}' is not a valid date in form of 'YYYY-mm-dd'"
            return render_template("trampoline/user_practices.html", body=body)

    practice_tables = []
    user_practices = Practice.load_from_db(username, date=None, skills=session.get("search_skills", ""))
    for practice in user_practices:
        if start_date and practice.date < start_date:
                continue
        if end_date and practice.date > end_date:
            continue

        # Add the turns into a table for that practice
        title_date = practice.date.strftime("%A %m/%d/%Y")
        title = f"{title_date} ({practice.event})"
        practice_table = skills_table(practice.turns, title=title, expand_comments=user.get("expand_comments", False))
        practice_tables.append(practice_table)

    all_practice_tables = "<br><br>".join(practice_tables)
   
    html = [
        # Div for practices so they are scrollable
        "<div id='practices' class='practices'><br><br>",
        all_practice_tables,
        "</div>"
    ]
    body = "".join(html) if all_practice_tables else ""
    return render_template("trampoline/user_practices.html", body=body)


@app.route("/logger", methods=['GET', 'POST'])
def trampoline_log():
    # POST/Redirect/GET to avoid resubmitting form on refresh
    if request.method == "POST":
        session["error"] = None
        try:
            _save_trampoline_data(request)
        except Exception as exception:
            session["error"] = f"Error saving log data: {exception}"
            logging.error(f"Error saving trampoline log data: {exception}")
            return redirect(url_for('trampoline_log', routine=request.form.get('log')))

        return redirect(url_for('trampoline_log'))

    # Require user to be logged in to use the app
    if not session.get("name"):
        return redirect(url_for('landing_page'))
    try:
        user = get_user(session.get('name'))
    except:
        session["previous_page"] = "trampoline_log"
        return redirect(url_for('logout'))
    
    # coaches go to coach home instead
    if user["is_coach"]:
        return redirect(url_for('coach_home'))

    username, event = current_user(), current_event()

    # Print out a table per date
    practice_tables = []

    # Get data from database
    user_practices = Practice.load_from_db(username, date=session.get("search_date"), skills=session.get("search_skills", ""))
    all_turns = []
    for practice in user_practices:
        # Add the turns into a table for that practice
        title_date = practice.date.strftime("%A %m/%d/%Y")
        title = f"{title_date} ({practice.event})"
        practice_table = skills_table(practice.turns, title=title, expand_comments=user.get("expand_comments", False))
        practice_tables.append(practice_table)
        for turn in practice.turns:
            all_turns.append([skill.shorthand for skill in turn.skills])

    all_practice_tables = "<br><br>".join(practice_tables)
    
    html = [
        #"<h1 style='text-align:center;' class=\"header\">Previous Practices</h1>",
        # Div for practices so they are scrollable
        "<div id='practices' class='practices'><br><br>",
        all_practice_tables,
        "</div>"
    ]
    body = "".join(html) if all_practice_tables else ""
    logging.info(f"error: {session.get('error', '')}")

    # Replace the log
    print(f"~~~~session log: {session.get('log', {})} - current date: {session.get('current_date')}")
    date_to_use = session.get('search_date') or session.get('current_date')
    if date_to_use:
        log_text = session.get('log', {}).get(date_to_use.strftime("%m-%d-%Y")) or request.args.get('routine', '')
    else:
        log_text = request.args.get('routine', '')
    return render_template(
        "trampoline/trampoline.html",
        body=body, username=username,
        event=event,
        routine_text=log_text,
        user=session.get('name'),
        goals=get_user_goals(current_user()),
        airtimes=get_user_airtimes(current_user()),
        all_skills=ALL_SKILLS,
        error_text=session.get('error'),
        search_date=session.get("search_date").strftime("%Y-%m-%d") if session.get("search_date") else None,
        current_date=session.get('current_date').strftime("%Y-%m-%d") if session.get('current_date') else None,
        search_skills=session.get("search_skills", ""),
        user_turns=all_turns
    )


@app.route("/logger/about")
def about_trampoline():
    commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode('ascii').strip()
    return render_template("trampoline/about_trampoline.html", user=session.get("name"), commit_hash=commit_hash)


@app.route("/about")
def about():
    commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode('ascii').strip()
    return render_template("pokemon/about.html", commit_hash=commit_hash)


@app.route("/move_image", methods=["GET", "POST"])
def move_count_image():
    pokemon_list = request.args.get("pokemon", "").split(",")
    num_cols = request.args.get("cols", 7)
    '''
    data = request.json
    print(data)
    pokemon_list = data.get("pokemon")
    num_cols = data.get("cols", 5)
    '''
    make_image(list(set(pokemon_list)), number_per_row=num_cols)
    export_image = os.path.join(app.root_path, "image.png")
    return send_file(export_image, as_attachment=True, cache_timeout=0)
    #return json.dumps({"status": "OK"})


@app.route("/move_counts")
def move_counts():
    chosen_pokemon = request.args.get('chosen_pokemon', None)
    n_moves = int(request.args.get('n_moves', 5))
    moves = get_move_counts(None, chosen_pokemon=chosen_pokemon, n_moves=n_moves)
    return render_template("pokemon/move_counts.html", moves=moves)

@app.route("/")
def run():
    user = None
    if session.get('name'):
        try:
            user = PokemonUser.load(session.get('name'))
        except:
            return redirect(url_for('pokemon_logout'))

    global CACHE
    global N_TEAMS
    chosen_league = request.args.get("league", None)
    if not chosen_league:
        if user and user.fav_league in LEAGUES_LIST.league_names:
            chosen_league = user.fav_league
        else:
            chosen_league = "ML"
    chosen_pokemon = request.args.get('pokemon', '')
    chosen_position = request.args.get('position', 'lead')
    num_days = int(request.args.get('num_days', '1'))
    rating = eval(request.args.get('rating', "None"))
    use_tooltip = bool(request.args.get('tooltips', False))
    use_weighted_values(bool(request.args.get('weights', False)))
    N_TEAMS = int(request.args.get('num_teams', N_TEAMS))
    html = []
    error_text = ""

    print("----- Refreshed -----")
    # Data tables from cache
    if get_refresh() or get_new_data(chosen_league, num_days, rating):
        try:
            results, team_maker, data_error = get_counters_for_rating(rating, chosen_league, days_back=num_days)
        except NoPokemonFound as exc:
            error_text = f"ERROR: Could not get data because: {str(exc)}. Using all data instead"
            results, team_maker = get_counters_for_rating(None, chosen_league, days_back=None)
        if data_error:
            error_text = f"ERROR: could not get data because: {data_error}. Using all data instead"
    else:
        results, team_maker, num_days, rating = CACHE.get('results').get(chosen_league), CACHE.get('team_maker').get(chosen_league), CACHE.get("num_days"), CACHE.get("rating")
        print("Did not refresh data because options are the same")
    cache_results = CACHE['results']
    cache_results[chosen_league] = results
    update_cache('results', cache_results)

    cache_team_maker = CACHE['team_maker']
    cache_team_maker[chosen_league] = team_maker
    update_cache('team_maker', cache_team_maker)
    update_cache('num_days', num_days)
    update_cache('rating', rating)
    update_cache('league', chosen_league)

    # Recommended teams
    #  make N_TEAMS unique teams. But try 2*N_TEAMS times to make unique teams
    team_results = make_recommended_teams(team_maker, chosen_pokemon, chosen_league, chosen_position)

    html.append("<h1 align='center'><u>Recommended Teams</u></h1>")
    html.append(create_table_from_results(team_results, width='50%'))

    # Data
    html.append("<h1 align='center'><u>Meta Data</u></h1>")
    #html.append("<div align='center'><button onclick='hideData()'>Toggle data</button></div>")
    #html.append("<div id='data' class='data'>")
    #tc = TeamCreater(team_maker)
    #html.append(create_table_from_results(results, pokemon=chosen_pokemon, width='75%', tc=tc, tooltip=use_tooltip))
    #html.append("</div>")

    return render_template(
        "pokemon/index.html",
        body="".join(html).replace(" table-responsive-lg", ""),
        leagues=sorted(LEAGUES_LIST.league_names),
        current_league=chosen_league,
        all_pokemon=sorted(team_maker.all_pokemon, key=lambda x: x.get('speciesId')),
        chosen_position=chosen_position,
        num_days=num_days,
        rating=rating,
        number_teams=N_TEAMS,
        current_pokemon=chosen_pokemon,
        error_text=error_text,
        result_data=team_maker.result_data,
        lead_move_count_string=','.join(pokemon[0] for pokemon in team_maker.result_data['meta_leads']),
        ss_move_count_string=','.join(pokemon[0] for pokemon in team_maker.result_data['meta_ss']),
        back_move_count_string=','.join(pokemon[0] for pokemon in team_maker.result_data['meta_backs']),
        poke_win_rates=team_maker.pokemon_win_rates,
        team_win_rates=team_maker.pokemon_teams,
        n_teams=sum([p[1] for p in team_maker.result_data['meta_leads']]),
        user=session.get("name", ""),
        ratings=sorted(team_maker.all_ratings),
        current_rating=rating,
        last_refreshed=team_maker.last_fetched.get(f"all_pokemon_{chosen_league}", "")
    )

@app.template_filter()
def pokemonColor(pokemon_name, chosen_pokemon, chosen_league):
    """ Choose the color of the pokemon"""
    if not chosen_pokemon:
        return pokemon_name.title()
    battle_results = get_simmed_battle(pokemon_name, chosen_pokemon)
    if not battle_results:
        tc = TeamCreater(CACHE['team_maker'][chosen_league])
        try:
            winner, leftover_health, battle_text = sim_battle(pokemon_name, chosen_pokemon, tc)
            add_simmed_battle(pokemon_name, chosen_pokemon, battle_text, winner, leftover_health)
            tool_tip_text = "&#013;&#010;</br>".join(battle_text)
            #logger.info(f"winner: {winner} - leftover_health: {leftover_health}")
        except Exception as exc:
            winner = None
            logger.error(f"{pokemon_name}")
            logger.error(traceback.format_exc())
            leftover_health = 0
            tool_tip_text=  ""
    else:
        winner = battle_results.get('winner')
        battle_text = battle_results.get('battle_text')
        leftover_health = battle_results.get('leftover_health')
        tool_tip_text = "&#013;&#010;</br>".join(battle_text)

    if winner == chosen_pokemon:
        text_color = "#00FF00"
        text_color = "#%02x%02x%02x" % (0, 100 + int(155 * leftover_health), 0)
    elif winner == pokemon_name:
        text_color = "#FF0000"
        text_color = "#%02x%02x%02x" % (100 + int(155 * leftover_health), 0, 0)
    else:
        text_color = "#000000"
    #logger.info(f"{cell_pokemon}: {text_color}")
    tooltip=True
    tooltip_addition = f"<span class='tooltiptext' id='{pokemon_name}-{chosen_pokemon}-battle'>{tool_tip_text}</span>" if tooltip else ""
    value = f"<a class='tooltip1' href='#' style='color: {text_color}; text-decoration: none;' target='_blank'>{pokemon_name.title()}{tooltip_addition}</a>"
    return value


@app.route("/pokemon/sign_up", methods=["GET", "POST"])
def pokemon_sign_up():
    """
    Sign up
    """
    if request.method == "POST":
        session["error"] = ""
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not username:
            session["error"] = "Please enter a username"
            return redirect(url_for('pokemon_sign_up'))
        try:
            PokemonUser.load(username)
            session["error"] = f"Username {username} already exists."
            return redirect(url_for('pokemon_sign_up'))
        except:
            pass
        if not password:
            session["error"] = "Missing Password"
            return redirect(url_for('pokemon_sign_up'))
        elif confirm != password:
            session["error"] = "Passwords do not match"
            return redirect(url_for('pokemon_sign_up'))
        if session.get('error'):
            return redirect(url_for('pokemon_sign_up'))
        # Create the user and go to login page
        default_teams = {"GL": {}, "UL": {}, "ML": {}, "Regionals": {}}
        hashed_password = sha256_crypt.encrypt(password)
        user = PokemonUser(username, hashed_password, "GL", default_teams)
        user.save()
        return redirect(url_for('pokemon_login'))
    return render_template("pokemon/sign_up.html", error_text=session.get('error'), user="")


@app.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    """
    Sign up
    """
    if request.method == "POST":
        session["error"] = ""
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        private = True if request.form.get("private")=="true" else False
        is_coach = True if request.form.get("user_type") == "coach" else False

        if not username:
            session["error"] = "Please enter a username"
            return redirect(url_for('sign_up'))
        try:
            get_user(username)
            session["error"] = f"Username {username} already exists."
            return redirect(url_for('sign_up'))
        except:
            pass
        if not password:
            session["error"] = "Missing Password"
            return redirect(url_for('sign_up'))
        elif confirm != password:
            session["error"] = "Passwords do not match"
            return redirect(url_for('sign_up'))
        if session.get('error'):
            return redirect(url_for('sign_up'))
        # Create the user and go to login page

        hashed_password = sha256_crypt.encrypt(password)
        athlete = Athlete(
            username, private, password=hashed_password,
            is_coach=is_coach, first_login=True, signup_date=datetime.datetime.today()
        )
        athlete.save()
        session["previous_page"] = "trampoline_log"
        return redirect(url_for('login'))
    return render_template("trampoline/sign_up.html", error_text=session.get('error'), user="")


@app.route("/pokemon/login", methods=["GET", "POST"])
def pokemon_login():
    """
    Login for the pokemon app
    """
    if request.method == "POST":
        global LOGGED_IN_USER
        session['error'] = ""
        username = request.form.get("username", "").lower()
        password = request.form.get('password')
        try:
            user = PokemonUser.load(username)
            if not user.password:
                hashed_password = sha256_crypt.encrypt("password")
                user.password = hashed_password
                user.save()
            if not sha256_crypt.verify(password, user.password):
                session['error'] = f"Incorrect password for user {username}"
            else:
                session['error'] = ""
        except Exception as load_err:
            print(f"\n\nError: {load_err}")
            session['error'] = f"Username {username} does not exists."
        if session.get('error'):
            return redirect(url_for('pokemon_login'))
        session["name"] = username
        return redirect(url_for('run'))
    return render_template("pokemon/login.html", user=session.get("name"), error_text=session.get('error'))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login
    """
    if request.method == "POST":
        global LOGGED_IN_USER
        session["error"] = ""
        username = request.form.get("username", "").lower()
        password = request.form.get("password")
        try:
            user = get_user(username)
            # if empty password then save as fake password
            if not user["password"]:
                hashed_password = sha256_crypt.encrypt("password")
                athlete = Athlete.load(username)
                athlete.password = hashed_password
                athlete.save()
                user["password"] = hashed_password
            if not sha256_crypt.verify(password, user["password"]):
                session["error"] = f"Incorrect password for user {username}"
                return redirect(url_for('login'))
        except Exception as login_err:
            session["error"] = f"Username {username} does not exists. {login_err}"
            return redirect(url_for('login'))
        session["name"] = username
        if session.get('name'):
            set_current_user(username)
            set_current_athlete(username)
        #return redirect(url_for('trampoline_log'))
        # no longer user's first login
        athlete = Athlete.load(username)
        print(str(athlete))
        if athlete.first_login:
            athlete.first_login = False
            athlete.save()
            print("First login for {username}")
            return redirect(url_for('about_trampoline'))
        return redirect(url_for(session.get('previous_page', 'trampoline_log')))
    return render_template("trampoline/login.html", user=session.get("name"), error_text=session.get('error'))


@app.route("/pokemon/logout", methods=["GET"])
def pokemon_logout():
    """
    Logout
    """
    global LOGGED_IN_USER
    LOGGED_IN_USER = ""
    session["name"] = None
    session['error'] = ""
    return redirect(url_for('pokemon_login'))


@app.route("/logout", methods=["GET"])
def logout():
    """
    Logout
    """
    global LOGGED_IN_USER
    LOGGED_IN_USER = ""
    session["name"] = None
    session["search_skills"] = ""
    session["search_date"] = None
    session["error"] = ""
    session["current_athlete"] = ""
    session["previous_page"] = "trampoline_log"
    session['log'] = {}
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
    return render_template("trampoline/landing_page.html", user=session.get("name"), leaderboard=leaderboard)


@app.route("/logger/coach/settings", methods=["GET", "POST"])
def coach_settings():
    """
    Coach settings
    """
    if request.method == "GET":
        users, _ = get_users_and_turns(only_users=True)
        current_user = Athlete.load(session.get('name'))
        print(current_user)
        messages = []
        for message in current_user.messages:
            if isinstance(message, str):
                message = {"read": False, "msg": message}
            messages.append(message)
        
        return render_template(
            "trampoline/coach_settings.html",
            users=users, user=session.get('name'),
            athletes=current_user.athletes,
            messages=messages
        )
    if request.method == "POST":
        athletes = request.form.getlist("coach_athletes")
        current_user = Athlete.load(session.get('name'))
        current_user.athletes = sorted(athletes)
        current_user.save()
        return redirect(url_for('coach_settings'))


@app.route('/logger/coach/messages', methods=["POST"])
def coach_message():
    """
    Send a message to athletes
    """
    current_user = Athlete.load(session.get('name'))

    # Handle new messages for athletes
    messages = request.form.get("message")
    if messages:
        print(f"messages: {messages}")
        now = datetime.datetime.now()
        new_message = f"{messages} - {current_user.name} {now.strftime('%Y-%m-%d %H:%M:%S')}"

        for athlete in current_user.athletes:
            a = Athlete.load(athlete)
            a.messages.append({"read": False, "msg":new_message})
            a.save()

    # Handle marking messages as read
    read_messages = {key:value for key, value in request.form.items() if key.startswith("message_")}
    print(f"read messages: {read_messages}")
    for message in range(len(current_user.messages)):
        current_msg = current_user.messages[message]
        if isinstance(current_msg, str):
            current_user.messages[message] = {'read': False, 'msg': current_msg}
        current_user.messages[message]['read'] = False

    for message in read_messages:
        message_num = int(message[8:]) - 1
        current_msg = current_user.messages[message_num]
        if isinstance(current_msg, str):
            current_user.messages[message_num] = {'read': False, 'msg': current_msg}
        current_user.messages[message_num]['read'] = True
    current_user.save()

    return redirect(url_for('coach_settings'))


@app.route('/logger/athlete/messages', methods=["POST"])
def athlete_message():
    """
    Send a message to the coach
    """
    users, _ = get_users_and_turns(only_users=True)
    current_user = Athlete.load(session.get('name'))
    messages = request.form.get("message")
    if messages:
        print(f"mesages: {messages}")
        now = datetime.datetime.now()
        new_message = f"{messages} - {current_user.name} {now.strftime('%Y-%m-%d %H:%M:%S')}"

        for username, user in users.items():
            if not user['is_coach']:
                continue
            if current_user.name in user['athletes']:
                coach = Athlete.load(username)
                coach.messages.append({"read": False, "msg":new_message})
                coach.save()
    
    read_messages = {key:value for key, value in request.form.items() if key.startswith("message_")}
    print(f"read messages: {read_messages}")
    for message in range(len(current_user.messages)):
        current_msg = current_user.messages[message]
        if isinstance(current_msg, str):
            current_user.messages[message] = {'read': False, 'msg': current_msg}
        current_user.messages[message]['read'] = False

    for message in read_messages:
        message_num = int(message[8:]) - 1
        current_msg = current_user.messages[message_num]
        if isinstance(current_msg, str):
            current_user.messages[message_num] = {'read': False, 'msg': current_msg}
        current_user.messages[message_num]['read'] = True
    current_user.save() 
    return redirect(url_for('user_profile'))



@app.route("/pokemon/user")
def pokemon_user_profile():
    """
    Pokmeon user profile
    """
    username = session.get('name')
    if not username:
        return redirect(url_for('pokemon_login'))
    user = PokemonUser.load(username)
    if 'Regionals' not in user.teams:
        user.teams["Regionals"] = {}
    print(f"\n\nteams: {user.teams}")
    if CACHE.get('team_maker', {}):
        all_team_makers = CACHE.get('team_maker', {})
    else:
        all_team_makers = {"GL": MetaTeamDestroyer(league="GL")}
        update_cache('team_maker', all_team_makers)

    # all pokemon are in the game master
    team_maker = list(all_team_makers.values())[0]
    regionals_data = []
    if len(user.teams["Regionals"]) == 2:
        gl_team_maker = all_team_makers.get('GL', MetaTeamDestroyer(league="GL"))
        all_team_makers['GL'] = gl_team_maker
        update_cache('team_maker', all_team_makers)
        regionals_data = gl_team_maker.get_regionals_data(user.teams["Regionals"])

    all_pokemon = []
    for pokemon in team_maker.game_master['pokemon']:
        all_pokemon.append(pokemon.get('speciesId'))

    all_pokemon = list(set(all_pokemon))
    all_pokemon = sorted(all_pokemon)

    return render_template(
        "pokemon/user_profile.html",
        user=username, userObj=user,
        leagues=sorted(LEAGUES_LIST.league_names),
        all_pokemon=all_pokemon,
        regionals_data=regionals_data,
        error_text=session.get('error'),
        )


@app.route("/logger/user/statistics")
def user_stats():
    """
    User statistics
    """
    username = session.get('name')
    if not username:
        session["previous_page"] = "user_stats"
        return redirect(url_for('login'))
    body = ""
    # Get user data
    user_turns = get_user_turns(username)
    airtimes = get_user_airtimes(username)
    print(f"user turns: {len(user_turns)}")

    # Collect all skills
    all_skills = defaultdict(lambda: {'all': 0, 'trampoline': 0, 'dmt': 0})
    dmt_passes = defaultdict(lambda: {'all': 0, 'trampoline': 0, 'dmt': 0})
    for turn in user_turns:
        skills = turn[1]
        event = turn[4]
        if skills.startswith('-'):
            continue
        routines = convert_form_data(skills, event=event, logger=None, get_athlete=False)
        if not routines:
            continue

        routines = routines[0]
        for s in routines.skills:
            skill = s.shorthand
            if skill in NON_SKILLS:
                continue

            all_skills[skill][event] += 1
            all_skills[skill]['all'] += 1
        
        # add double mini passes
        if event == "dmt" and len(routines.skills) == 2:
            dmt_skills = [s.shorthand for s in routines.skills]
            if 'X' in dmt_skills:
                continue
            dmt_pass = ' '.join(dmt_skills)
            dmt_passes[dmt_pass]['dmt'] += 1
            dmt_passes[dmt_pass]['all'] += 1

    print(f"---- dmt passes: {dmt_passes}") 
    # print the tables
    tables = []
    
    all_skills_ordered = OrderedDict()
    print(all_skills.keys())
    all_keys = [key for key in all_skills.keys() if len(key) > 1]
    for key in sorted(all_keys, key=lambda x: int(x[:-1]) if len(x)>1 else x):
        all_skills_ordered[key] = all_skills[key]
    # add dmt passes
    dmt_passes_ordered = OrderedDict()
    for key in sorted(dmt_passes.keys(), key=lambda x: (x.split()[0][:-1], x.split()[1][:-1])):
        #all_skills_ordered[key] = dmt_passes[key]
        dmt_passes_ordered[key] = dmt_passes[key]
    print(all_skills_ordered)

    body = ""
    # User charts
    start_date = request.args.get('chart_start')
    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%m/%d/%Y")
    end_date = request.args.get('chart_end')
    if end_date:
        end_date = datetime.datetime.strptime(end_date, "%m/%d/%Y")

    current_user = session.get('name')
    if not session.get("name"):
        session["previous_page"] = "user_stats"
        return redirect(url_for('login'))
    # get user from db
    try:
        user_data = get_user(current_user)
    except Exception as exc:
        logger.error(f"Exception: {exc}")
        user_data = {}

    if user_data["is_coach"]:
        return redirect(url_for("coach_settings"))

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

            # notes also have empty turns
            if not turn['turn'] and turn['note']:
                continue

            # skip other users
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

    # airtimes data
    datapts['airtimes'] = [{'x': airtime['date'], 'y': float(airtime['airtime'])} for airtime in airtimes if airtime['airtime']]
    return render_template(
        "trampoline/user_statistics.html",
        body=body,
        user=session.get('name'),
        datapts=datapts,
        chart_start=request.args.get('chart_start', ""),
        chart_end=request.args.get('chart_end', ""),
        error_text=session.get('error'),
        all_skills=all_skills_ordered,
        dmt_passes=dmt_passes_ordered
    )

@app.route("/logger/user")
def user_profile():
    """
    User profile
    """
    current_user = session.get('name')
    if not session.get("name"):
        session["previous_page"] = "user_profile"
        return redirect(url_for('login'))
    # get user from db
    try:
        user_data = get_user(current_user)
    except Exception as exc:
        logger.error(f"Exception: {exc}")
        user_data = {}

    if user_data["is_coach"]:
        return redirect(url_for("coach_settings"))
    
    messages = []
    for message in user_data['messages']:
        if isinstance(message, str):
            message = {"read": False, "msg": message}
        messages.append(message)

    return render_template(
        "trampoline/user_profile.html",
        user=current_user,
        user_data=user_data,
        error_text=session.get('error'),
        messages=messages
    )


@app.route("/pokemon/user/update", methods=["POST"])
def pokemon_update_user():
    """
    Update user
    """
    user = PokemonUser.load(session.get('name'))

    # update prefered league
    league = request.form.get('league')
    user.fav_league = league
    
    # update password
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    if old_password:
        if sha256_crypt.verify(old_password, user.password):
            if not new_password:
                session['error'] = "Please enter a new password"
            else:
                user.password = sha256_crypt.encrypt(new_password)
                session['error'] = ""
        else:
            session['error'] = "Did not update password for user because old password was incorrect"

    # update pokemon teams
    selected_pokemon = {
        key[7:]: pokemon
        for key, pokemon in sorted(request.form.items(), key=lambda x: x[0])
        if key.startswith("select-")
    }
    print(selected_pokemon)
    print(list(request.form.items()))
    teams = {"GL": {}, "UL": {}, "ML": {}, "Regionals": {}}
    pokemon_keys = sorted(selected_pokemon.keys())
    for key in pokemon_keys:
        pokemon = selected_pokemon[key]
        print(f"\n\n{key} {pokemon}")
        try:
            league_key, x, _ = key.split("-")
        except:
            continue
        if x not in teams[league_key]:
            teams[league_key][x] = []
        teams[league_key][x].append(pokemon)
    print(teams)
    user.teams = teams
    user.save()
    return redirect(url_for("pokemon_user_profile"))



@app.route("/logger/user/update", methods=["POST"])
def update_user():
    """
    Update user
    """
    private = True if request.form.get("private")=="true" else False
    expand_comments = True if request.form.get("expand")=="true" else False
    compulsory = request.form.get("compulsory")
    optional = request.form.get("optional")
    athlete = Athlete.load(session.get("name"))

    # update password
    session['error'] = ""
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    if old_password:
        if sha256_crypt.verify(old_password, athlete.password):
            if not new_password:
                session['error'] = "Please enter a new password"
            else:
                athlete.password = sha256_crypt.encrypt(new_password)
        else:
            session['error'] = "Did not update password for user because old password was incorrect"

    athlete.private = private
    athlete.compulsory = [skill for skill in compulsory.split()]
    athlete.optional = [skill for skill in optional.split()]
    athlete.expand_comments = expand_comments
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
        turns_file.write("turn number, skills, date, event, notes\n")
        for turn in user_turns:
            turn_date = str(turn[2]).split()[0]
            turn_skills = turn[1]
            notes = turn[5].lstrip('- ').lstrip('-')
            # If the turn is only a note then turn it into the turn
            if not turn_skills and notes:
                line = f"{turn[0]}, {notes}, {turn_date}, {turn[4]}, \n"
            else:
                line = f"{turn[0]}, {turn_skills}, {turn_date}, {turn[4]}, {turn[5]}\n"
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