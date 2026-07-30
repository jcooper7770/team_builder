from flask import Blueprint, session, send_file, request, render_template, redirect

from application.trampoline.trampoline import Athlete, Practice
from application.utils.database import get_user
from application.utils.utils import *

comp_card_bp = Blueprint('comp_cards', __name__)


@comp_card_bp.route("/logger/user/compcard", methods=["GET", "POST"])
def user_comp_card():
    """
    Create comp card for the user
    """
    athlete = Athlete.load(session.get("name"))
    if request.method == "GET":
        athlete.save_comp_card()
    else:
        routine1 = request.json.get('r1')
        routine2 = request.json.get('r2')
        routines = [
            routine1 or athlete.compulsory,
            routine2 or athlete.optional
        ]
        athlete.save_comp_card(routines=routines, more_data=request.json)
    return send_file("comp_cards/modified_comp_card.pdf", as_attachment=True)

@comp_card_bp.route("/logger/user/compcard/download")
def download_comp_card():
    """
    Downloads the comp card
    """
    filename = request.args.get("filename", "modified_comp_card.pdf")
    return send_file(f"comp_cards/{filename}", as_attachment=True)


@comp_card_bp.route("/logger/user/dm_compcard", methods=["GET", "POST"])
def user_dm_comp_card():
    """
    Create double mini comp card for the user
    """
    athlete = Athlete.load(session.get("name"))
    if request.method == "GET":
        athlete.save_dm_comp_card()
    else:
        pass1 = request.json.get('p1')
        pass2 = request.json.get('p2')
        passes = [
            pass1 or athlete.dm_prelim1,
            pass2 or athlete.dm_prelim2
        ]
        athlete.save_dm_comp_card(passes=passes, more_data=request.json)

    return send_file("comp_cards/modified_comp_card.pdf", as_attachment=True)


@comp_card_bp.route("/logger/coach/compcards")
def coach_comp_cards():
    """
    Create comp cards for the coach's athletes
    """
    import zipfile
    coach = Athlete.load(session.get("name"))
    zipfile_name = "Comp_cards.zip"
    zipf = zipfile.ZipFile(zipfile_name,'w', zipfile.ZIP_DEFLATED)
    for athlete_name in coach.athletes:
        athlete = Athlete.load(athlete_name)
        athlete.save_comp_card(f"{athlete_name}_tramp.pdf")
        zipf.write(f"comp_cards/{athlete_name}_tramp.pdf")
        athlete.save_dm_comp_card(f"{athlete_name}_dmt.pdf")
        zipf.write(f"comp_cards/{athlete_name}_dmt.pdf")
    
    zipf.close()
    return send_file(zipfile_name, mimetype='zip', as_attachment=True)


@comp_card_bp.route("/logger/compcards")
def comp_cards():
    """
    Create comp cards manually
    """
    name = session.get('name')
    if not name:
        return redirect('/login')
    user_practices = Practice.load_from_db(name)
    all_turns = []
    for practice in user_practices:
        for turn in practice.turns:
            all_turns.append([skill.shorthand for skill in turn.skills])
    athlete = Athlete.load(name)
    athlete_name = f"{athlete.details['first_name']} {athlete.details['last_name']}" if athlete.details['first_name'] else ""
    user_data = get_user(session.get('name'))
    return render_template(
        "trampoline/comp_card.html",
        user=name,
        name=athlete_name,
        user_data=user_data,
        user_turns=all_turns
    )