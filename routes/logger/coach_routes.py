import datetime
import re
import json

from flask import Blueprint, render_template, request, session, redirect, url_for

from application.trampoline.trampoline import Practice, current_user, Athlete, ALL_SKILLS
from application.utils.database import get_users_and_turns, get_user_goals, add_lesson_to_db, get_lessons_from_db, delete_lesson_from_db
from application.utils.utils import *

coach_bp = Blueprint('coach', __name__)

@coach_bp.route("/logger/coach/home", methods=['GET'])
def coach_home():
    """
    Home for coaches
    """
    username = session.get('name')
    coach = Athlete.load(username)
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
        print(practice["practice"].__dict__)
        practice_table = skills_table(practice['practice'].turns, title=title, expand_comments=False, tags=practice['practice'].tags)
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
    users, _ = get_users_and_turns(only_users=True)

    lesson_plans = get_lessons_from_db(username)

    return render_template(
        "trampoline/coach_home.html",
        body=body,
        athletes=coach.athletes,
        current_athlete=current_athlete,
        current_date=session.get('current_date').strftime("%Y-%m-%d") if session.get('current_date') else None,
        user=session.get('name'),
        goals=get_user_goals(current_user()),
        error_text=session.get('error'),
        search_date=session.get("search_date").strftime("%Y-%m-%d") if session.get("search_date") else None,
        search_skills=session.get("search_skills", ""),
        user_turns=[],
        tags=["Competition", "Pit Training"],
        all_skills=ALL_SKILLS,
        users=users,
        lesson_plans=lesson_plans
    )

@coach_bp.route("/logger/coach/settings", methods=["GET", "POST"])
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
            requests=current_user.coach_requests,
            messages=messages
        )
    if request.method == "POST":
        athletes = request.form.getlist("coach_athletes")
        current_user = Athlete.load(session.get('name'))
        new_athletes, new_requests = [], []
        for athlete_username in athletes:
            if athlete_username in current_user.athletes:
                new_athletes.append(athlete_username)
            else:
                new_requests.append(athlete_username)

        #current_user.athletes = sorted(athletes)
        current_user.athletes = sorted(new_athletes)
        current_user.coach_requests = sorted(new_requests)
        current_user.save()

        # Go tell the athletes that the coaches requested
        for athlete in new_requests:
            user = Athlete.load(athlete)
            requests = user.coach_requests
            if current_user.name not in requests:
                requests.append(current_user.name)
                user.coach_requests = sorted(requests)
                user.save()
        return redirect(url_for('coach.coach_settings'))


@coach_bp.route('/logger/coach/messages', methods=["POST"])
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

    return redirect(url_for('coach.coach_settings'))


@coach_bp.route('/logger/coach/lesson', methods=["POST", "DELETE"])
def new_lesson_plan():
    """
    Make or delete a new lesson plan
    """
    coach = session.get('name')
    title = request.json.get('title')
    date = request.json.get('date')
    if request.method == "DELETE":
        delete_lesson_from_db(coach, title, date)
        return {"success": True}

    # Check if lesson plan already exists
    lesson_plans = get_lessons_from_db(session.get('name'))
    existing = [plan for plan in lesson_plans if plan.get('title') == title and plan.get('date') == date]
    if existing:
        return {"success": False, "error": "A lesson plan already exists by this title for this date"}
    description = request.json.get('description')
    plans = json.dumps(request.json.get('plans'))
    save_type = request.json.get('saveType', 'new')
    add_lesson_to_db(title, description, date, coach, plans, new=save_type == "new")
    return {
        'success': True
    }