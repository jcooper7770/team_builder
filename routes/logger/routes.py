import datetime
import os
from collections import defaultdict, OrderedDict

from flask import Blueprint, jsonify, render_template, request, session, redirect, send_file, url_for, flash
import subprocess
from passlib.hash import sha256_crypt
from werkzeug.utils import secure_filename

from application.trampoline.challenges import CHALLENGES, get_next_sunday, save_completed_challenges, retroactively_record_challenges, retroactively_save_in_bg
from application.trampoline.trampoline import convert_form_data, get_leaderboards, pretty_print, Practice, current_user, set_current_user,\
     current_event, set_current_event, set_current_athlete,\
     ALL_SKILLS, get_leaderboards, Athlete, get_user_turns, get_turn_dds
from application.utils.database import get_users_and_turns, insert_goal_to_db, get_user_goals, complete_goal,\
    delete_goal_from_db, get_user, add_airtime_to_db, get_user_airtimes, delete_airtime_from_db,\
    rate_practice_in_db, get_ratings, add_post_to_db, get_posts_from_db, delete_post_from_db,\
    get_lessons_from_db, update_lesson
from application.utils.utils import *

tramp_bp = Blueprint('trampoline', __name__)
UPLOAD_FOLDER = os.path.join("static", "uploads")


def get_log_data(request):
    """
    Returns the data from the logs as a list
    """
    form_data_list = []
    for key in request.form.keys():
        print(key)
        if key.startswith("log-"):
            log_data = request.form.get(key)
            if log_data:
                form_data_list.append(log_data)
    return form_data_list


def _save_trampoline_data(request):
    """
    Saves the routine data from the forms
    """
    # Convert form data to trampoline skills
    form_data = request.form.get('log', '')
    logger.info(f"Form data: {form_data}")
    form_data_list = get_log_data(request)
    form_data = "\n".join(form_data_list)
    logger.info(f"Form data: {form_data}")
    #username = request.form.get('name', None) or current_user()
    username = request.form.get('name', None) or session.get('name')
    event = request.form.get('event', None) or current_event()
    notes = request.form.get('notes', None)
    tags = request.form.get('selected_tags', '').split(',')
    custom_tags = request.form.get("custom_tags", "").split(',')
    tags.extend(custom_tags)
    save_type = request.form.get("save-type", "new")
    set_current_event(event)
    #set_current_user(username)
    set_current_athlete(username)
    logger.info(f"Username: {username}")
    '''
    user_data = get_user(username)
    personal_dict = user_data.get('details', {}).get('personal_dict', {})
    print(f"Personal dict: {personal_dict}")
    print(user_data)
    routines = convert_form_data(form_data, event=event, notes=notes, athlete_dict=personal_dict)
    '''
    routines = convert_form_data(form_data, event=event, notes=notes, athlete_dict={})
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
    practice = Practice(form_date.date(), routines, event, tags)
    #replace_practice = session.get('log', {}).get(form_date.strftime('%m-%d-%Y')) is not None
    replace_practice = save_type == "edit"
    print(f"~~~~~~~~~~~~replace: {replace_practice} - log {session.get('log')} - date {form_date.strftime('%m-%d-%Y')}")
    saved_practice = practice.save(replace=replace_practice, user=username)
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


@tramp_bp.route("/logger", methods=['GET', 'POST'])
def trampoline_log():
    # POST/Redirect/GET to avoid resubmitting form on refresh
    if request.method == "POST":
        endpoint = request.form.get("endpoint")
        get_endpoint = "coach.coach_home" if endpoint == "coach" else "trampoline.trampoline_log"
        session["error"] = None
        try:
            _save_trampoline_data(request)
        except Exception as exception:
            session["error"] = f"Error saving log data: {exception}"
            logging.error(f"Error saving trampoline log data: {exception}")
            log_data = get_log_data(request)
            return redirect(url_for(get_endpoint, routine=request.form.get('log'), log_lines=','.join(log_data)))

        return redirect(url_for(get_endpoint))


    # Require user to be logged in to use the app
    if not session.get("name"):
        return redirect(url_for('trampoline.landing_page'))
    try:
        user = get_user(session.get('name'))
    except:
        session["previous_page"] = "trampoline.trampoline_log"
        return redirect(url_for('trampoline.logout'))
    
    # coaches go to coach home instead
    if user["is_coach"]:
        return redirect(url_for('coach.coach_home'))

    username, event = current_user(), current_event()

    # Print out a table per date
    practice_tables = []

    # Get data from database
    user_practices = Practice.load_from_db(username, date=session.get("search_date"), skills=session.get("search_skills", ""))
    all_turns = []
    all_ratings = get_ratings(session.get('name'))
    print(all_ratings)
    for practice in user_practices:
        # Add the turns into a table for that practice
        title_date = practice.date.strftime("%A %m/%d/%Y")
        rating_date = practice.date.strftime("%m-%d-%Y")
        num_turns = practice.get_num_turns()
        title = f"{title_date} ({practice.event}) ({num_turns} {'turns' if num_turns > 1 else 'turn'})"
        practice_rating = all_ratings.get(f"{rating_date}_{practice.event}", 0)
        print(f"practice {title} rating: {practice_rating}")
        practice_table = skills_table(practice.turns, title=title, expand_comments=user.get("expand_comments", False), rating=practice_rating, tags=practice.tags)
        practice_tables.append(practice_table)
        for turn in practice.turns:
            all_turns.append([skill.shorthand for skill in turn.skills])

    all_practice_tables = "".join(practice_tables)
    
    html = [
        #"<h1 style='text-align:center;' class=\"header\">Previous Practices</h1>",
        # Div for practices so they are scrollable
        #"<div id='practices' class='practices'><br><br>",
        "<div id='practices' class=''><br><br>",
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
    users, _ = get_users_and_turns(only_users=True)

    # stats page stuff
    # Get user data
    user_turns = get_user_turns(username)
    airtimes = get_user_airtimes(username)
    print(f"user turns: {len(user_turns)}")

    # Make tables and datapts
    all_skills_ordered, dmt_passes_ordered, tumbling_skills_ordered = create_skill_tables(user_turns)
    datapts = create_user_stats(request, airtimes)

    # get coaches
    coaches = []
    for coach_name, user_details in users.items():
        if not user_details.get('is_coach'):
            continue
        if username in user_details.get('athletes'):
            coaches.append(coach_name)
    
    all_lesson_plans = get_lessons_from_db(None)
    lesson_plans = [lesson_plan for lesson_plan in all_lesson_plans if lesson_plan.get('coach') in coaches]

    # mark full lesson as complete if all done
    for lesson_num, lesson_plan in enumerate(lesson_plans):
        all_done = False
        complete_percent = 0
        if username in lesson_plans[lesson_num].get('athletes_completed', {}):
            remaining_turns = set(lesson_plan['plans']) - set(lesson_plan['athletes_completed'][username])
            all_done = len(remaining_turns) == 0
            complete_percent = (len(lesson_plan['plans']) - len(remaining_turns)) / len(lesson_plan['plans']) * 100

        lesson_plans[lesson_num]['completed'] = all_done
        lesson_plans[lesson_num]['percent_complete'] = f"{complete_percent:0.2f}"
    print(lesson_plans)

    challenges = {
        "Do a routine": True,
        "Get airtime higher than 20.00": False
    }
    challenges = {
        challenge.name: challenge.complete_fn(user_turns, airtimes)
        for challenge in CHALLENGES
    }
    next_sunday = get_next_sunday()

    # Put completed challenges into athlete db (in background)
    save_completed_challenges(username, challenges)
    if request.args.get('save_all_challenges', False):
        print("Retroactively saving challenges for all user data")
        retroactively_save_in_bg(username, user_turns, airtimes)
    
    if request.args.get('delete_challenges', False):
        print("Deleting user challenges")
        athlete = Athlete.load(username)
        athlete.details['completed_challenges'] = {}
        athlete.save()

    return render_template(
        f"trampoline/trampoline.html",
        body=body, username=username,
        event=event,
        routine_text=log_text,
        user=session.get('name'),
        goals=get_user_goals(current_user()),
        airtimes=airtimes,
        all_skills=ALL_SKILLS,
        error_text=session.get('error'),
        search_date=session.get("search_date").strftime("%Y-%m-%d") if session.get("search_date") else None,
        current_date=session.get('current_date').strftime("%Y-%m-%d") if session.get('current_date') else None,
        search_skills=session.get("search_skills", ""),
        user_turns=all_turns,
        tags=["Competition", "Pit Training"],
        log_lines=request.args.get('log_lines', '').split(','),
        users=users,
        # user stats stuff
        datapts=datapts,
        chart_start=request.args.get('chart_start', ""),
        chart_end=request.args.get('chart_end', ""),
        all_skills_table=all_skills_ordered,
        dmt_passes=dmt_passes_ordered,
        tumbling_skills=tumbling_skills_ordered,
        lesson_plans=lesson_plans,
        athlete_dict=user['details'].get('personal_dict', {}),
        challenges=challenges,
        next_sunday=next_sunday
    )


@tramp_bp.route("/logger/_clear")
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


@tramp_bp.route("/logger/_clearDay")
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


@tramp_bp.route("/logger/edit/<day>/<event>")
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
    return redirect(url_for("trampoline.trampoline_log"))


@tramp_bp.route("/logger/delete/<day>/<event>")
def delete_day(day, event):
    """
    Deletes the given day and event
    """
    datetime_to_remove = datetime.datetime.strptime(day, "%m-%d-%Y")
    Practice.delete(datetime_to_remove, event=event)
    return redirect(url_for("trampoline.trampoline_log"))


@tramp_bp.route("/logger/search/skills", methods=["POST"])
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
    return redirect(url_for('trampoline.trampoline_log'))

@tramp_bp.route("/logger/rate_practice", methods=["POST"])
def rate_practice():
    practice_date = request.json.get("date")
    rating = request.json.get("rating")
    practice, event = practice_date.split("_")
    print(f"Rating {practice} ({event}): {rating}")
    rate_practice_in_db(practice, event, rating, session.get('name'))
    return {"success": True}

@tramp_bp.route("/logger/search", methods=["POST", "GET"])
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
    return redirect(url_for("trampoline.trampoline_log"))
 
@tramp_bp.route("/logger/<username>/practices", methods=['GET'])
def trampoline_user_practices(username):
    """
    Return user practices
    """
    user = None
    if username == "_current_":
        username = session.get('name')
        return redirect(url_for('trampoline.trampoline_user_practices', username=username, **request.args))

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
    all_ratings = get_ratings(user)
    print(all_ratings)
    user_practices = Practice.load_from_db(username, date=None, skills=session.get("search_skills", ""))
    for practice in user_practices:
        if start_date and practice.date < start_date:
                continue
        if end_date and practice.date > end_date:
            continue

        # Add the turns into a table for that practice
        title_date = practice.date.strftime("%A %m/%d/%Y")
        num_turns = practice.get_num_turns()
        title = f"{title_date} ({practice.event}) ({num_turns} {'turns' if num_turns > 1 else 'turn'})"
        practice_rating = all_ratings.get(f"{title_date}_{practice.event}", 0)
        print(f"practice {title} rating: {practice_rating}")
        practice_table = skills_table(practice.turns, title=title, expand_comments=user.get("expand_comments", False), rating=practice_rating, tags=practice.tags, editable=False)
        practice_tables.append(practice_table)

    all_practice_tables = "".join(practice_tables)
   
    html = [
        # Div for practices so they are scrollable
        "<div id='practices'><br><br>",
        all_practice_tables,
        "</div>"
    ]
    body = "".join(html) if all_practice_tables else ""
    return render_template("trampoline/user_practices.html", body=body)


@tramp_bp.route("/logger/about")
def about_trampoline():
    commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode('ascii').strip()
    return render_template("trampoline/about_trampoline.html", user=session.get("name"), commit_hash=commit_hash)


@tramp_bp.route("/logger/resources")
def resource_trampoline():
    return render_template("trampoline/resources.html", user=session.get("name"))


@tramp_bp.route("/sign_up", methods=["GET", "POST"])
def sign_up():
    """
    Sign up
    """
    if request.method == "POST":
        session["error"] = ""
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        private = True if request.form.get("private")=="true" else False
        is_coach = True if request.form.get("user_type") == "coach" else False
        levels = [
            request.form.get("tramp_level"),
            request.form.get("dmt_level"),
            request.form.get("tu_level"),
        ]

        if not username:
            session["error"] = "Please enter a username"
            return redirect(url_for('trampoline.login'))
        try:
            get_user(username)
            session["error"] = f"Username {username} already exists."
            return redirect(url_for('trampoline.login'))
        except:
            pass
        if not password:
            session["error"] = "Missing Password"
            return redirect(url_for('trampoline.login'))
        elif confirm != password:
            session["error"] = "Passwords do not match"
            return redirect(url_for('trampoline.login'))
        if session.get('error'):
            return redirect(url_for('trampoline.login'))
        # Create the user and go to login page

        hashed_password = sha256_crypt.encrypt(password)
        athlete = Athlete(
            username, private, password=hashed_password,
            is_coach=is_coach, first_login=True, signup_date=datetime.datetime.today(),
            first_name=first_name, last_name=last_name,
            tramp_level=levels[0], dmt_level=levels[1], tumbling_level=levels[2],
        )
        athlete.save()
        session["previous_page"] = "trampoline.trampoline_log"
        return redirect(url_for('trampoline.login'))
    return render_template("trampoline/login.html", error_text=session.get('error'), user="")

@tramp_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Login
    """
    if request.method == "POST":
        global LOGGED_IN_USER
        session["error"] = ""
        username = request.form.get("username", "").lower()
        password = request.form.get("password")
        '''
        user = get_user(username)
        print(f"login user0: {user}")
        # if empty password then save as fake password
        if not user["password"]:
            print(f"login user1: {user}")
            hashed_password = sha256_crypt.encrypt("password")
            athlete = Athlete.load(username)
            print(f"login user2: {user}")
            athlete.password = hashed_password
            athlete.save()
            print(f"login user3: {user}")
            user["password"] = hashed_password
        if not sha256_crypt.verify(password, user["password"]):
            session["error"] = f"Incorrect password for user {username}"
            return redirect(url_for('trampoline.login'))
        '''
        try:
            user = get_user(username)
            print(f"login user0: {user}")
            # if empty password then save as fake password
            if not user["password"]:
                print(f"login user1: {user}")
                hashed_password = sha256_crypt.encrypt("password")
                athlete = Athlete.load(username)
                print(f"login user2: {user}")
                athlete.password = hashed_password
                athlete.save()
                print(f"login user3: {user}")
                user["password"] = hashed_password
            if not sha256_crypt.verify(password, user["password"]):
                session["error"] = f"Incorrect password for user {username}"
                return redirect(url_for('trampoline.login'))
        except Exception as login_err:
            session["error"] = f"Username {username} does not exists. {login_err}"
            return redirect(url_for('trampoline.login'))
        session["name"] = username
        if session.get('name'):
            set_current_user(username)
            set_current_athlete(username)
        #return redirect(url_for('trampoline.trampoline_log'))
        # no longer user's first login
        athlete = Athlete.load(username)
        print(str(athlete))
        if athlete.first_login:
            athlete.first_login = False
            athlete.save()
            print("First login for {username}")
            return redirect(url_for('trampoline.about_trampoline'))
        return redirect(url_for(session.get('previous_page', 'trampoline.trampoline_log')))
    return render_template("trampoline/login.html", user=session.get("name"), error_text=session.get('error'))


@tramp_bp.route("/logout", methods=["GET"])
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
    session["previous_page"] = "trampoline.trampoline_log"
    session['log'] = {}
    return redirect(url_for('trampoline.login'))


@tramp_bp.route("/logger/landing")
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


@tramp_bp.route('/logger/social/post', methods=["POST", "DELETE"])
def make_post():
    """
    Adds a post to the db
    """
    if request.method == "DELETE":
        print("testing")
        name = request.json.get('name')
        date = request.json.get('date').split('-')[1].strip()
        file_to_delete = request.json.get('file')
        try:
            print(delete_post_from_db(name.strip(), date))
            os.remove(file_to_delete)
            return {"success": True}
        except Exception as error:
            return {"success": False, "error": str(error)}
    #current_user = Athlete.load(session.get('name'))
    name = session.get('name')
    #post = request.json.get("post")
    #date = request.json.get("date")
    post = request.form.get('post')
    date = request.form.get('date')
    #post_file = request.json.get('file')
    post_file = request.files.get('file')
    print(f"file: {post_file}")
    filename = ""
    if post_file:
        filename = os.path.join(UPLOAD_FOLDER, post_file.filename)
        post_file.save(filename)
    add_post_to_db(name, date, post, filename)
    return {"success": True}


@tramp_bp.route('/logger/practice/post', methods=["POST"])
def make_practice_post():
    """
    Adds a post to the db
    """
    #current_user = Athlete.load(session.get('name'))
    name = session.get('name')
    turns, _ = get_turn_dds(name)
    practice = request.json.get('practice')
    tags = request.json.get('tags', [])
    date, event = practice.split('_')
    practice_turns = [turn for turn in turns[event] if turn['date'].strftime("%m-%d-%Y")==date]
    total_flips = sum([turn['flips'] for turn in practice_turns])
    #month, day, year = date.split("-")
    #formatted_date = f"{month}/{day}/{year} 00:00:00 AM"
    now = datetime.datetime.now()
    formatted_date = now.strftime('%m/%d/%Y %H:%M:%S %p')
    post = f"Posting practice from {date} on {event}"
    post = f"[{event}] I submitted a practice (on {date}) with {len(practice_turns)} turns, totaling {total_flips} flips!"
    tagsText = " ".join(f"#{tag.replace(' ', '')}" for tag in tags)
    post = f"""[{event}] I submitted a practice (on {date}) with {len(practice_turns)} turns, totaling {total_flips} flips!
    {tagsText}"""
    add_post_to_db(name, formatted_date, post, filename="")
    return {"success": True}


@tramp_bp.route('/logger/social/video/post', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('trampoline.social'))
    file = request.files['file']
    if file.filename == '':
        flash('No image selected for uploading')
        return redirect(url_for('trampoline.social'))
    else:
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        #print('upload_video filename: ' + filename)
        flash('Video successfully uploaded and displayed below')
        return redirect(url_for('trampoline.social'))


@tramp_bp.route('/display/<filename>')
def display_video(filename):
	#print('display_video filename: ' + filename)
	return redirect(url_for('static', filename='uploads/' + filename), code=301)


@tramp_bp.route('/logger/athlete/messages', methods=["POST"])
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
    return redirect(url_for('trampoline.user_profile'))




@tramp_bp.route("/logger/user/statistics")
def user_stats():
    """
    User statistics
    """
    username = session.get('name')
    if not username:
        session["previous_page"] = "trampoline.user_stats"
        return redirect(url_for('trampoline.login'))
    body = ""

    # get user from db
    try:
        user_data = get_user(username)
    except Exception as exc:
        logger.error(f"Exception: {exc}")
        user_data = {}

    if user_data.get("is_coach", False):
        return redirect(url_for("coach.coach_settings"))

    # Get user data
    user_turns = get_user_turns(username)
    airtimes = get_user_airtimes(username)
    print(f"user turns: {len(user_turns)}")

    # Make tables and datapts
    all_skills_ordered, dmt_passes_ordered, tumbling_skills_ordered = create_skill_tables(user_turns)
    datapts = create_user_stats(request, airtimes)
    return render_template(
        "trampoline/user_statistics.html",
        body=body,
        user=session.get('name'),
        datapts=datapts,
        chart_start=request.args.get('chart_start', ""),
        chart_end=request.args.get('chart_end', ""),
        error_text=session.get('error'),
        all_skills=all_skills_ordered,
        dmt_passes=dmt_passes_ordered,
        tumbling_skills=tumbling_skills_ordered
    )


def create_skill_tables(user_turns):
    """
    Create the data for the skill tables on stats page
    """
    all_skills = defaultdict(lambda: {'all': 0, 'trampoline': 0, 'dmt': 0, 'tumbling': 0})
    dmt_passes = defaultdict(lambda: {'all': 0, 'trampoline': 0, 'dmt': 0, 'tumbling': 0})
    tumbling_skills = defaultdict(lambda: {'all': 0, 'trampoline': 0, 'dmt': 0, 'tumbling': 0})
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

            if event != "tumbling":
                all_skills[skill][event] += 1
                all_skills[skill]['all'] += 1
            else:
                tumbling_skills[skill][event] += 1

        # add double mini passes
        if event == "dmt" and len(routines.skills) == 2:
            dmt_skills = [s.shorthand for s in routines.skills]
            if 'X' in dmt_skills:
                continue
            dmt_pass = ' '.join(dmt_skills)
            dmt_passes[dmt_pass]['dmt'] += 1
            dmt_passes[dmt_pass]['all'] += 1

    #print(f"---- dmt passes: {dmt_passes}") 
    # print the tables
    #tables = []
    
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
    # order tumbling skills
    tumbling_skills_ordered = OrderedDict()
    for key in sorted(tumbling_skills.keys(), key=lambda x: (len(x), x)):
        tumbling_skills_ordered[key] = tumbling_skills[key]
    print(all_skills_ordered)
    return all_skills_ordered, dmt_passes_ordered, tumbling_skills_ordered


def get_user_prestige(username):
    """
    Return's the user's total points
    """
    data = {
        "days": 0,
        "routines": 0,
        "biggest_combo_days": 0,
        "double_point_modifiers": 0,
        "quadruple_point_modifiers": 0
    }
    class MockReq:
        args = {}
    mock_request = MockReq()
    stats = create_user_stats(mock_request, [], username=username)
    data['trampoline_routines'] = sum([stat['y'] for stat in stats.get('trampoline_routines')])
    tramp_day_points = 0 # number of points for logging days
    last_date = None
    combo = 1 # combo for # days in a row
    for datapt in stats.get("trampoline_flips_per_day", []):
        date = datetime.datetime.strptime(datapt['x'], "%Y-%m-%d")
        data["days"] += 1
        #start_date = datetime.datetime.strptime(start_date, "%m/%d/%Y")
        if not last_date:
            tramp_day_points += 1
            print(f"prestige calc: {date} === {tramp_day_points}")
            last_date = date
            continue
        if (date - last_date).days == 1:
            combo += 1
            
            points_added = 1
            if 2 <= combo < 7:
                print("combo 2-6 days! - +2 pts")
                points_added = 2
                data["double_point_modifiers"] += 1
            elif combo >= 7:
                print("combo 7+ days! - +4 pts")
                points_added = 4
                data["quadruple_point_modifiers"] += 1

            tramp_day_points += points_added
            print(f"prestige calc: {date} === {tramp_day_points}")
            last_date = date
            if combo > data["biggest_combo_days"]:
                data["biggest_combo_days"] = combo
            continue
        # no longer consecutive days so combo goes back to 1
        combo = 1
        tramp_day_points += 1
        print(f"prestige calc: {date} === {tramp_day_points}")
        last_date = date
    result = {
        "trampoline": tramp_day_points + 3*data['trampoline_routines']
    }
    result.update(data)
    return result


def create_user_stats(request, airtimes, username=None):
    """
    Create all datapoints for user stats
    """
    current_user = username or session.get('name')
    start_date = request.args.get('chart_start')
    if start_date:
        start_date = datetime.datetime.strptime(start_date, "%m/%d/%Y")
    end_date = request.args.get('chart_end')
    if end_date:
        end_date = datetime.datetime.strptime(end_date, "%m/%d/%Y")

    event_turns, _ = get_turn_dds()
    datapts = {}
    day_flips = {
        'trampoline': defaultdict(int),
        'dmt': defaultdict(int),
        'tumbling': defaultdict(int)
    }
    day_routines = {
        'trampoline': defaultdict(int),
        'dmt': defaultdict(int),
        'tumbling': defaultdict(int)
    }
    flips_per_turn = {
        'trampoline': defaultdict(list),
        'dmt': defaultdict(list),
        'tumbling': defaultdict(list)
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

            # routines/passes
            if event == "trampoline":
                if is_routine(turn['turn']):
                    day_routines[event][turn_date] += 1
    
    datapts['trampoline_flips_per_day'] = [{'x': date, 'y': flips} for date, flips in sorted(day_flips['trampoline'].items(), key=lambda x: x[0])]
    datapts['dmt_flips_per_day'] = [{'x': date, 'y': flips} for date, flips in day_flips['dmt'].items()]
    datapts['dmt_flips_per_turn'] = [{'x': date, 'y': sum(flips)/len(flips)} for date, flips in flips_per_turn['dmt'].items()]
    datapts['trampoline_flips_per_turn'] = [{'x': date, 'y': sum(flips)/len(flips)} for date, flips in flips_per_turn['trampoline'].items()]
    datapts['tumbling_flips_per_day'] = [{'x': date, 'y': flips} for date, flips in day_flips['tumbling'].items()]
    datapts['tumbling_flips_per_turn'] = [{'x': date, 'y': sum(flips)/len(flips)} for date, flips in flips_per_turn['tumbling'].items()]
    datapts['turns_per_practice'] = [{'x': date, 'y': turns} for date, turns in sorted(turns_per_practice.items(), key=lambda x: x[0])]
    datapts['trampoline_routines'] = [{'x': date, 'y': routines} for date, routines in sorted(day_routines['trampoline'].items(), key=lambda x: x[0])]

    # airtimes data
    datapts['airtimes'] = [{'x': airtime['date'], 'y': float(airtime['airtime'])} for airtime in airtimes if airtime['airtime']]
    return datapts


@tramp_bp.route("/logger/user")
def user_profile():
    """
    User profile
    """
    current_user = session.get('name')
    if not session.get("name"):
        session["previous_page"] = "trampoline.user_profile"
        return redirect(url_for('trampoline.login'))
    # get user from db
    try:
        user_data = get_user(current_user)
    except Exception as exc:
        logger.error(f"Exception: {exc}")
        user_data = {}

    if user_data["is_coach"]:
        return redirect(url_for("coach.coach_settings"))
    
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

@tramp_bp.route("/logger/user/requests", methods=["POST"])
def coach_request():
    """
    Approve or Deny coach requests
    """
    request_id = request.form['id']
    print(request_id)

    username = session.get('name')
    current_user = Athlete.load(username)
    if "approve" in request_id:
        coach_name = request_id[16:]

        # Move athlete from requests to coach's athletes
        coach = Athlete.load(coach_name)
        coach.coach_requests = [request for request in coach.coach_requests if request != username]
        print(f"Adding {username} to {coach.athletes}")
        coach.athletes.append(username)
        coach.athletes = sorted(coach.athletes)
        coach.save()

        # Remove coach from athlete requests
        current_user.coach_requests = [request for request in current_user.coach_requests if request != coach_name]
        current_user.save()
    elif "deny" in request_id:
        coach_name = request_id[13:]
        
        # Remove athlete from coach requests
        coach = Athlete.load(coach_name)
        coach.coach_requests = [request for request in coach.coach_requests if request != username]
        coach.save()

        # Remove coach from athlete requests
        current_user.coach_requests = [request for request in current_user.coach_requests if request != coach_name]
        current_user.save()


    return {"success": True}

@tramp_bp.route("/logger/user/update", methods=["POST"])
def update_user():
    """
    Update user
    """
    private = True if request.form.get("private")=="true" else False
    expand_comments = True if request.form.get("expand")=="true" else False
    compulsory = request.form.get("compulsory")
    optional = request.form.get("optional")
    pass1 = request.form.get('pass1')
    pass2 = request.form.get('pass2')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    tu_pass1 = request.form.get('tu-pass1')
    tu_pass2 = request.form.get('tu-pass2')
    tramp_level = request.form.get('level-tramp')
    dmt_level = request.form.get('level-dmt')
    tumbling_level = request.form.get('level-tu')
    dict_keys = [value for key, value in request.form.items() if key.startswith("dict_name") and value != ""]
    dict_values = [value for key, value in request.form.items() if key.startswith("dict_skill") and value != ""]
    print(f"keys: {dict_keys} - values: {dict_values}")
    athlete_dict = dict(zip(dict_keys, dict_values))
    print(athlete_dict)
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
    athlete.dm_prelim1 = [skill for skill in pass1.split()]
    athlete.dm_prelim2 = [skill for skill in pass2.split()]
    athlete.tu_prelim1 = [skill for skill in tu_pass1.split()]
    athlete.tu_prelim2 = [skill for skill in tu_pass2.split()]
    athlete.levels = [tramp_level, dmt_level, tumbling_level]
    athlete.details['first_name'] = first_name
    athlete.details['last_name'] = last_name
    athlete.details["personal_dict"] = athlete_dict
    athlete.save()
    return redirect(url_for("trampoline.user_profile"))


@tramp_bp.route("/logger/user/export", methods=["GET", "POST"])
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
    export_dir = os.path.join(tramp_bp.root_path, "exported_data")
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


@tramp_bp.route("/logger/chart", methods=["GET"])
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


@tramp_bp.route("/logger/social", methods=["GET"])
def social():
    current_user = session.get('name', '')
    all_posts = get_posts_from_db()
    # Sort posts by date
    all_posts = sorted(all_posts, key=lambda x: datetime.datetime.strptime(x['date'], "%m/%d/%Y %H:%M:%S %p"))
    return render_template("trampoline/social.html", user=current_user, all_posts=all_posts)


@tramp_bp.route("/logger/user/<name>", methods=["GET"])
def user_page(name):
    current_user = session.get('name')
    #event_turns, user_data = get_turn_dds()
    all_posts = get_posts_from_db()
    user_posts = [post for post in all_posts if post.get('name') == name]
    # Sort posts by date
    user_posts = sorted(user_posts, key=lambda x: datetime.datetime.strptime(x['date'], "%m/%d/%Y %H:%M:%S %p"), reverse=True)
    try:
        user = Athlete.load(name)
        name = user.name
    except:
        name = ""
    
    prestige = get_user_prestige(name)
    print(f"prestige data: {prestige}")
    turns, _ = get_turn_dds(name)
    total_flips, total_turns, biggest_flips, biggest_dd = 0, 0, 0, 0
    for event, event_turns in turns.items():
        for turn in event_turns:
            n_flips = turn["flips"]
            total_flips += n_flips
            total_turns += 1

            if n_flips > biggest_flips:
                biggest_flips = n_flips
            
            n_dd = turn['dd']
            if n_dd > biggest_dd:
                biggest_dd = n_dd

    print(f"completed challenges: {user.details.get('completed_challenges')}")
    completed_challenges = [
        {'title': title, "challenges": challenges}
        for title, challenges in user.details.get('completed_challenges', {}).items()
        if challenges
    ]
    sorted_challenges = sorted(completed_challenges, key=lambda x: x['title'])
    total_completed_challenges = sum([len(challenge['challenges']) for challenge in completed_challenges])

    private_profile = user.private if name != "" else True
    if name == current_user:
        private_profile = False
    return render_template(
        "trampoline/user_page.html",
        user=current_user,
        name=name,
        athlete_comp=user.compulsory if name != "" else "",
        athlete_optional=user.optional if name != "" else "",
        athlete_details=user.details if name != "" else {},
        dm1=user.dm_prelim1 if name != "" else "",
        dm2=user.dm_prelim2 if name != "" else "",
        private=private_profile,
        tramp_level=user.levels[0] if name != "" else "",
        dmt_level=user.levels[1] if name != "" else "",
        tumbling_level=user.levels[2] if name != "" else "",
        total_flips=total_flips,
        total_turns=total_turns,
        biggest_flips=biggest_flips,
        biggest_dd=biggest_dd,
        user_posts=user_posts,
        prestige=prestige,
        completed_challenges=sorted_challenges,
        total_completed_challenges=total_completed_challenges
    )

@tramp_bp.route('/logger/lessons/complete', methods=["POST"])
def complete_lesson():
    """
    Complete a lesson for an athlete
    """
    #current_user = Athlete.load(session.get('name'))
    name = session.get('name')
    title = request.json.get('title')
    finished_turns = request.json.get('finishedTurns')
    date = request.json.get('date')

    lessons = get_lessons_from_db(None)
    all_finished_turns = {name: []}
    for lesson in lessons:
        print(f"lesson: {lesson}")
        if lesson['title'] == title and lesson['date'] == date:
            all_finished_turns = lesson['athletes_completed']
            break
    print(all_finished_turns)
    all_finished_turns[name] = finished_turns
    update_lesson(title, date, all_finished_turns)
    return {"success": True}