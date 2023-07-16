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
  - [DONE] Add tumbling
  - [DONE] Add links to DD sheets (from USAG)
  - Move routines and passes to a new table
"""
import socket
import traceback

from flask import Flask
from flask_session import Session

from application.pokemon.subscription import sub_bp
from application.pokemon.team_building import TeamCreater
from application.pokemon.battle_sim import sim_battle
from application.utils.database import set_table_name, get_simmed_battle, add_simmed_battle
from application.utils.utils import *

from routes.logger.routes import tramp_bp
from routes.logger.comp_card_routes import comp_card_bp
from routes.logger.coach_routes import coach_bp
from routes.pokemon.routes import poke_bp

app = Flask(__name__, static_url_path="", static_folder="static")
app.config["CACHE_TYPE"] = "null"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.secret_key = 'your_secret_key'
Session(app)

app.register_blueprint(sub_bp, url_prefix="/sub")
app.register_blueprint(poke_bp, url_prefix="/")
app.register_blueprint(tramp_bp, url_prefix="/")
app.register_blueprint(comp_card_bp, url_prefix="/")
app.register_blueprint(coach_bp, url_prefix="/")


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