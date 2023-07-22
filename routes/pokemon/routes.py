import os

from flask import Blueprint, render_template, request, session, redirect, send_file, url_for
import subprocess
import traceback
from passlib.hash import sha256_crypt

from application.pokemon.leagues import LEAGUES_LIST
from application.pokemon.move_counts import get_move_counts, make_image, get_all_rankings
from application.pokemon.team_building import MetaTeamDestroyer, PokemonUser, get_counters_for_rating, NoPokemonFound, get_recent_league,\
    use_weighted_values, get_refresh, create_table_from_results, set_refresh
from application.utils.utils import *

poke_bp = Blueprint('pokemon', __name__)
N_TEAMS = 3

def get_new_data(league, num_days_start, num_days_end, rating):
    diff_league = CACHE.get("results", {}).get(league) is None
    diff_days_start = CACHE.get("num_days_start") != num_days_start
    diff_days_end = CACHE.get("num_days_end") != num_days_end
    diff_rating = CACHE.get("rating") != rating
    return diff_league or diff_days_start or diff_days_end or diff_rating


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




@poke_bp.route("/pokemon", methods=["GET"])
def pokemon_landing():
    """
    Pokemon landing page
    """
    return render_template("pokemon/landing_page.html")


@poke_bp.route("/about")
def about():
    commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode('ascii').strip()
    return render_template("pokemon/about.html", commit_hash=commit_hash)


@poke_bp.route("/move_image", methods=["GET", "POST"])
def move_count_image():
    pokemon_list = request.args.get("pokemon", "").split(",")
    num_cols = int(request.args.get("cols", 7))
    reset = bool(request.args.get('reset', False))
    '''
    data = request.json
    print(data)
    pokemon_list = data.get("pokemon")
    num_cols = data.get("cols", 5)
    '''
    make_image(list(set(pokemon_list)), number_per_row=num_cols, reset_data=reset)
    export_image = os.path.join(poke_bp.root_path, "image.png")
    #return send_file(export_image, as_attachment=True, cache_timeout=0)
    return send_file(export_image, as_attachment=True)
    #return json.dumps({"status": "OK"})


@poke_bp.route("/move_counts")
def move_counts():
    chosen_pokemon = request.args.get('chosen_pokemon', None)
    n_moves = int(request.args.get('n_moves', 5))
    moves = get_move_counts(None, chosen_pokemon=chosen_pokemon, n_moves=n_moves)
    return render_template("pokemon/move_counts.html", moves=moves)

@poke_bp.route("/")
def run():
    user = None
    if session.get('name'):
        try:
            user = PokemonUser.load(session.get('name'))
        except:
            return redirect(url_for('pokemon.pokemon_logout'))

    global CACHE
    global N_TEAMS
    chosen_league = request.args.get("league", session.get('league'))
    if not chosen_league:
        if user and user.fav_league in LEAGUES_LIST.league_names:
            chosen_league = user.fav_league
        else:
            chosen_league = get_recent_league() or "GL"
            session['league'] = chosen_league
            #chosen_league = "ML"
    print(f"Chosen league: {chosen_league}. {session.get('league')}")
    session['league'] = chosen_league
    chosen_pokemon = request.args.get('pokemon', '')
    chosen_position = request.args.get('position', 'lead')
    num_days_start = int(request.args.get('num_days_start', '1'))
    num_days_end = int(request.args.get('num_days_end', '0'))
    rating = eval(request.args.get('rating', "None"))
    use_tooltip = bool(request.args.get('tooltips', False))
    use_weighted_values(bool(request.args.get('weights', False)))
    N_TEAMS = int(request.args.get('num_teams', N_TEAMS))
    html = []
    error_text = ""

    print("----- Refreshed -----")
    # Data tables from cache
    if get_refresh() or get_new_data(chosen_league, num_days_start, num_days_end, rating):
        try:
            #results, team_maker, data_error = get_counters_for_rating(rating, chosen_league, days_back=num_days)
            results, team_maker, data_error = get_counters_for_rating(rating, chosen_league, days_back_start=num_days_start, days_back_end=num_days_end)
        except NoPokemonFound as exc:
            error_text = f"ERROR: Could not get data because: {str(exc)}. Using all data instead"
            results, team_maker = get_counters_for_rating(None, chosen_league, days_back_start=None, days_back_end=None)
        if data_error:
            error_text = f"ERROR: could not get data because: {data_error}. Using all data instead"
    else:
        results, team_maker, num_days_start, num_days_end, rating = CACHE.get('results').get(chosen_league), CACHE.get('team_maker').get(chosen_league), CACHE.get("num_days_start"), CACHE.get('num_days_end'), CACHE.get("rating")
        print("Did not refresh data because options are the same")
    cache_results = CACHE['results']
    cache_results[chosen_league] = results
    update_cache('results', cache_results)

    cache_team_maker = CACHE['team_maker']
    cache_team_maker[chosen_league] = team_maker
    update_cache('team_maker', cache_team_maker)
    update_cache('num_days_start', num_days_start)
    update_cache('num_days_end', num_days_end)
    update_cache('rating', rating)
    update_cache('league', chosen_league)

    # Recommended teams
    #  make N_TEAMS unique teams. But try 2*N_TEAMS times to make unique teams
    team_results = make_recommended_teams(team_maker, chosen_pokemon, chosen_league, chosen_position)

    html.append("<h1 align='center'><u>Randomly Generated Teams</u></h1>")
    html.append(create_table_from_results(team_results, width='50%'))

    # Data
    #html.append("<div align='center'><button onclick='hideData()'>Toggle data</button></div>")
    #html.append("<div id='data' class='data'>")
    #tc = TeamCreater(team_maker)
    #html.append(create_table_from_results(results, pokemon=chosen_pokemon, width='75%', tc=tc, tooltip=use_tooltip))
    #html.append("</div>")

    # make a list of pokemon from the teams
    teams_pokemon = set()
    for team in team_maker.pokemon_teams:
        for pokemon in team.split('-'):
            teams_pokemon.add(pokemon)
    return render_template(
        "pokemon/index.html",
        body="".join(html).replace(" table-responsive-lg", ""),
        leagues=sorted(LEAGUES_LIST.league_names),
        split_leagues=LEAGUES_LIST.league_groups,
        current_league=chosen_league,
        all_pokemon=sorted(team_maker.all_pokemon, key=lambda x: x.get('speciesId')),
        chosen_position=chosen_position,
        num_days_start=num_days_start,
        num_days_end=num_days_end,
        rating=rating,
        number_teams=N_TEAMS,
        current_pokemon=chosen_pokemon,
        error_text=error_text,
        result_data=team_maker.result_data,
        lead_move_count_string=','.join(pokemon[0] for pokemon in team_maker.result_data['meta_leads']),
        ss_move_count_string=','.join(pokemon[0] for pokemon in team_maker.result_data['meta_ss']),
        back_move_count_string=','.join(pokemon[0] for pokemon in team_maker.result_data['meta_backs']),
        teams_move_count_string=','.join(teams_pokemon),
        poke_win_rates=team_maker.pokemon_win_rates,
        team_win_rates=team_maker.pokemon_teams,
        n_teams=sum([p[1] for p in team_maker.result_data['meta_leads']]),
        user=session.get("name", ""),
        ratings=sorted(team_maker.all_ratings),
        current_rating=rating,
        last_refreshed=team_maker.last_fetched.get(f"all_pokemon_{chosen_league}", "")
    )

@poke_bp.route("/pokemon/login", methods=["GET", "POST"])
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
            return redirect(url_for('pokemon.pokemon_login'))
        session["name"] = username
        return redirect(url_for('pokemon.run'))
    return render_template("pokemon/login.html", user=session.get("name"), error_text=session.get('error'))



@poke_bp.route("/pokemon/logout", methods=["GET"])
def pokemon_logout():
    """
    Logout
    """
    global LOGGED_IN_USER
    LOGGED_IN_USER = ""
    session["name"] = None
    session['error'] = ""
    return redirect(url_for('pokemon.pokemon_login'))


@poke_bp.route("/pokemon/sign_up", methods=["GET", "POST"])
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
            return redirect(url_for('pokemon.pokemon_sign_up'))
        try:
            PokemonUser.load(username)
            session["error"] = f"Username {username} already exists."
            return redirect(url_for('pokemon.pokemon_sign_up'))
        except:
            pass
        if not password:
            session["error"] = "Missing Password"
            return redirect(url_for('pokemon.pokemon_sign_up'))
        elif confirm != password:
            session["error"] = "Passwords do not match"
            return redirect(url_for('pokemon.pokemon_sign_up'))
        if session.get('error'):
            return redirect(url_for('pokemon.pokemon_sign_up'))
        # Create the user and go to login page
        default_teams = {"GL": {}, "UL": {}, "ML": {}, "Regionals": {}}
        hashed_password = sha256_crypt.encrypt(password)
        user = PokemonUser(username, hashed_password, "GL", default_teams)
        user.save()
        return redirect(url_for('pokemon.pokemon_login'))
    return render_template("pokemon/sign_up.html", error_text=session.get('error'), user="")


@poke_bp.route("/data/refresh", methods=["POST"])
def refresh_pokemon_data():
    """
    Refreshes the league data
    """
    data = request.get_json()
    logger.info(f"\n\n\nRefreshing data for {data}")
    set_refresh(True)
    #return jsonify(status="success")
    return "success"


@poke_bp.route("/pokemon/user")
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


@poke_bp.route("/pokemon/user/update", methods=["POST"])
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
    return redirect(url_for("pokemon.pokemon_user_profile"))


