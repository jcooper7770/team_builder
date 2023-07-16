from flask import Blueprint, session, send_file

from application.trampoline.trampoline import Athlete
from application.utils.utils import *

comp_card_bp = Blueprint('comp_cards', __name__)


@comp_card_bp.route("/logger/user/compcard")
def user_comp_card():
    """
    Create comp card for the user
    """
    athlete = Athlete.load(session.get("name"))
    athlete.save_comp_card()
    return send_file("comp_cards/modified_comp_card.pdf", as_attachment=True)


@comp_card_bp.route("/logger/user/dm_compcard")
def user_dm_comp_card():
    """
    Create double mini comp card for the user
    """
    athlete = Athlete.load(session.get("name"))
    athlete.save_dm_comp_card()
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

