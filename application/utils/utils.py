"""

 Todo:
  - Round tables using <div class="card">
"""


import traceback

import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('werkzeug') # grabs underlying WSGI logger
handler = logging.FileHandler('test.log') # creates handler for the log file
logger.addHandler(handler) # adds handler to the werkzeug WSGI logger


NON_SKILLS = [
    "X", "...", '--', '%'
]
CACHE = {'results': {}, 'team_maker': {}, 'num_days': 1, 'rating': None}
TYPE_EFFECTIVENESS = {
    "Bug": {
        "Bug": 1.0,
        "Dark": 1.6,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 0.625,
        "Fighting": 0.625,
        "Fire": 0.625,
        "Flying": 0.625,
        "Ghost": 0.625,
        "Grass": 1.6,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 0.625,
        "Psychic": 1.6,
        "Rock": 1.0,
        "Steel": 0.625,
        "Water": 1.0
    },
    "Dark": {
        "Bug": 1.0,
        "Dark": 0.625,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 0.625,
        "Fighting": 0.625,
        "Fire": 1.0,
        "Flying": 1.0,
        "Ghost": 1.6,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.6,
        "Rock": 1.0,
        "Steel": 1.0,
        "Water": 1.0
    },
    "Dragon": {
        "Bug": 1.0,
        "Dark": 1.0,
        "Dragon": 1.6,
        "Electric": 1.0,
        "Fairy": 0.390625,
        "Fighting": 1.0,
        "Fire": 1.0,
        "Flying": 1.0,
        "Ghost": 1.0,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 1.0,
        "Steel": 0.625,
        "Water": 1.0
    },
    "Electric": {
        "Bug": 1.0,
        "Dark": 1.0,
        "Dragon": 0.625,
        "Electric": 0.625,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 1.0,
        "Flying": 1.6,
        "Ghost": 1.0,
        "Grass": 0.625,
        "Ground": 0.390625,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 1.0,
        "Steel": 1.0,
        "Water": 1.6
    },
    "Fairy": {
        "Bug": 1.0,
        "Dark": 1.6,
        "Dragon": 1.6,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.6,
        "Fire": 0.625,
        "Flying": 1.0,
        "Ghost": 1.0,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 0.625,
        "Psychic": 1.0,
        "Rock": 1.0,
        "Steel": 0.625,
        "Water": 1.0
    },
    "Fighting": {
        "Bug": 0.625,
        "Dark": 1.6,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 0.625,
        "Fighting": 1.0,
        "Fire": 1.0,
        "Flying": 0.625,
        "Ghost": 0.390625,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.6,
        "Normal": 1.6,
        "Poison": 0.625,
        "Psychic": 0.625,
        "Rock": 1.6,
        "Steel": 1.6,
        "Water": 1.0
    },
    "Fire": {
        "Bug": 1.6,
        "Dark": 1.0,
        "Dragon": 0.625,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 0.625,
        "Flying": 1.0,
        "Ghost": 1.0,
        "Grass": 1.6,
        "Ground": 1.0,
        "Ice": 1.6,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 0.625,
        "Steel": 1.6,
        "Water": 0.625
    },
    "Flying": {
        "Bug": 1.6,
        "Dark": 1.0,
        "Dragon": 1.0,
        "Electric": 0.625,
        "Fairy": 1.0,
        "Fighting": 1.6,
        "Fire": 1.0,
        "Flying": 1.0,
        "Ghost": 1.0,
        "Grass": 1.6,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 0.625,
        "Steel": 0.625,
        "Water": 1.0
    },
    "Ghost": {
        "Bug": 1.0,
        "Dark": 0.625,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 1.0,
        "Flying": 1.0,
        "Ghost": 1.6,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 0.390625,
        "Poison": 1.0,
        "Psychic": 1.6,
        "Rock": 1.0,
        "Steel": 1.0,
        "Water": 1.0
    },
    "Grass": {
        "Bug": 0.625,
        "Dark": 1.0,
        "Dragon": 0.625,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 0.625,
        "Flying": 0.625,
        "Ghost": 1.0,
        "Grass": 0.625,
        "Ground": 1.6,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 0.625,
        "Psychic": 1.0,
        "Rock": 1.6,
        "Steel": 0.625,
        "Water": 1.6
    },
    "Ground": {
        "Bug": 0.625,
        "Dark": 1.0,
        "Dragon": 1.0,
        "Electric": 1.6,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 1.6,
        "Flying": 0.390625,
        "Ghost": 1.0,
        "Grass": 0.625,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.6,
        "Psychic": 1.0,
        "Rock": 1.6,
        "Steel": 1.6,
        "Water": 1.0
    },
    "Ice": {
        "Bug": 1.0,
        "Dark": 1.0,
        "Dragon": 1.6,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 0.625,
        "Flying": 1.6,
        "Ghost": 1.0,
        "Grass": 1.6,
        "Ground": 1.6,
        "Ice": 0.625,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 1.0,
        "Steel": 0.625,
        "Water": 0.625
    },
    "Normal": {
        "Bug": 1.0,
        "Dark": 1.0,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 1.0,
        "Flying": 1.0,
        "Ghost": 0.390625,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 0.625,
        "Steel": 0.625,
        "Water": 1.0
    },
    "Poison": {
        "Bug": 1.0,
        "Dark": 1.0,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 1.6,
        "Fighting": 1.0,
        "Fire": 1.0,
        "Flying": 1.0,
        "Ghost": 0.625,
        "Grass": 1.6,
        "Ground": 0.625,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 0.625,
        "Psychic": 1.0,
        "Rock": 0.625,
        "Steel": 0.390625,
        "Water": 1.0
    },
    "Psychic": {
        "Bug": 1.0,
        "Dark": 0.390625,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.6,
        "Fire": 1.0,
        "Flying": 1.0,
        "Ghost": 1.0,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.6,
        "Psychic": 0.625,
        "Rock": 1.0,
        "Steel": 0.625,
        "Water": 1.0
    },
    "Rock": {
        "Bug": 1.6,
        "Dark": 1.0,
        "Dragon": 1.0,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 0.625,
        "Fire": 1.6,
        "Flying": 1.6,
        "Ghost": 1.0,
        "Grass": 1.0,
        "Ground": 0.625,
        "Ice": 1.6,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 1.0,
        "Steel": 0.625,
        "Water": 1.0
    },
    "Steel": {
        "Bug": 1.0,
        "Dark": 1.0,
        "Dragon": 1.0,
        "Electric": 0.625,
        "Fairy": 1.6,
        "Fighting": 1.0,
        "Fire": 0.625,
        "Flying": 1.0,
        "Ghost": 1.0,
        "Grass": 1.0,
        "Ground": 1.0,
        "Ice": 1.6,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 1.6,
        "Steel": 0.625,
        "Water": 0.625
    },
    "Water": {
        "Bug": 1.0,
        "Dark": 1.0,
        "Dragon": 0.625,
        "Electric": 1.0,
        "Fairy": 1.0,
        "Fighting": 1.0,
        "Fire": 1.6,
        "Flying": 1.0,
        "Ghost": 1.0,
        "Grass": 0.625,
        "Ground": 1.6,
        "Ice": 1.0,
        "Normal": 1.0,
        "Poison": 1.0,
        "Psychic": 1.0,
        "Rock": 1.6,
        "Steel": 1.0,
        "Water": 0.625
    }
}


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
        self._row_num = 0
        
    def new_table(self):
        options = [
            f"border='{self.border}'",
            f"align='{self.align}'",
            #f"style='background-color:{self.bgcolor};'",
            'class="table table-striped table-responsive-lg table-light color-changing"'
        ]
        if self.width:
            options.append(f"width='{self.width}'")
            # This is the correct way to do it but this breaks the home page
            #options.append(f"style='width:{self.width}'")
        options_str = " ".join(options)
        self.table.append('<div class="container">')
        self.table.append(f"<table {options_str}>")
        self.table.append("<thead class=\"thead-dark bg-dark text-white color-changing\">")
        self._row_num = 0

    def end_table(self):
        self.table.append("</tbody></table></div>")
        self._row_num = 0

    def new_row(self, styles=""):           
        styles_text = f' styles="{styles}"' if styles else ''
        self.table.append(f"<tr{styles_text}>")
        self._row_num += 1

    def end_row(self):
        self.table.append("</tr>")
        if self._row_num == 1:
            #self.table.append("</thead><tbody style=\"background: white;\">")
            self.table.append("</thead><tbody>")

    def new_line(self):
        self.table.append("<br>")

    def new_header(self, value, colspan, rating=None, tags=[], editable=True):
        ratings_dict ={"3": "😊", "2": "😐", "1": "😞", "0": ""}
        self.new_row()
        try:
            rating_text = f'<span id="practice-rating" name="{rating}">{ratings_dict.get(str(rating)) if rating else ""}</span>'
            date_to_remove = value.split()[1].replace("/", '-')
            event_to_remove = value.split()[2].replace("(", "").replace(")", "")
            share_date = f"{date_to_remove.split('-')[2]}-{date_to_remove.split('-')[0]}-{date_to_remove.split('-')[1]}"
            share_a, edit_a, delete_a = "", "", ""
            if editable:
                share_a=f"<a href='/logger/_current_/practices?start={share_date}&end={share_date}' class='btn-rate float-right' target='_blank' title='share practice'>Share</a>"
                edit_a = f'<button type="button" class="btn float-right"><a title="edit day" href="#"><span id="edit_{date_to_remove}_{event_to_remove}" class="fa fa-pencil-square-o" aria-hidden=\'true\'></span></button>'
                delete_a = f'<button type="button" class="btn float-right" id="delete-button"><a title="remove day" href="#"><span id="remove_{date_to_remove}_{event_to_remove}" class="fa fa-remove" aria-hidden=\'true\'></span></button>'
            options_div = f'<div style="display: none;" class="extra-options">{edit_a}{share_a}</div>'
            tag_divs = [f'<div class="practice-tag">{tag}</div>' for tag in tags if tag]
            #self.table.append(f'<th id="practice-header" colspan={colspan} align="center" name="{date_to_remove}_{event_to_remove}">{rating_text}{value}{delete_a}{edit_a}{share_a}</th>')
            content = f'<div class="row"><div class="col-md-12" id="practice-header">{rating_text}{value}{delete_a}{edit_a}{share_a}</div></div><div class="row">{"".join(tag_divs)}</div>'
            self.table.append(f'<th colspan={colspan} align="center" name="{date_to_remove}_{event_to_remove}">{content}</th>')
        except:
            tag_divs = [f'<div class="practice-tag">{tag}</div>' for tag in tags if tag]
            self.table.append(f'<th colspan={colspan} align="center"><div class="row">{value}</div><div class="row tags-row">{"".join(tag_divs)}</div></th>')
        self.end_row()

    def reset_table(self):
        if not self.first_table:
            self.end_row()
            self.end_table()
            self.new_line()
            self.new_table()
            self.new_row()
            
        self.first_table = False

    def add_cell(self, value, colspan=None, align=None, width=None, classList=None):
        colspan_text = f" colspan={colspan}" if colspan else ""
        align_text = f" align='{align}'" if align else ""
        width_text = f" width='{width}'" if width else ""
        class_text = f' class="{classList}"' if classList else ""
        self.table.append(f"<td{colspan_text}{align_text}{width_text}{class_text}>{value}</td>")

    def render(self):
        return "".join(self.table)


def skills_table(skills, title="Routines", expand_comments=False, rating=None, tags=[], editable=True):
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
    skills_table.new_header(title, colspan=most_cols+8, rating=rating, tags=tags, editable=editable)
    total_turn_num = 0
    
    for turn_num, turn in enumerate(skills):
        skills_table.new_row()
        if turn.note and not turn.skills:
            cell = f'<i class="fa fa-comments"></i> {turn.note}'
            skills_table.add_cell(cell, colspan=most_cols+8, classList="comment-row")
            skills_table.new_row()
        if not turn.skills:
            continue
        total_turn_num += 1
        # Turn number (also a link to copy the turn)
        routine_str = ' '.join(skill.shorthand for skill in turn.skills)
        #skills_table.add_cell(f"<b><a id='copy-text' title='Copy text' href='/logger?routine={routine_str}'>{total_turn_num}</a></b>")
        #skills_table.add_cell(f"<b><a id='copy-text' title='Copy text' href='#'>{total_turn_num}</a></b>")

        note_html = ""
        if turn.note:
            display = "none" if not expand_comments else "inline"
            hidden_note = f'<span id="hidden-note" style="display:{display};"><br><i>{turn.note}</i></span>'
            note_html = f' <i title="toggle comment" class="fa fa-comments" id="unhide-note"></i> {hidden_note}'
        #skills_table.add_cell(f"<b><a id='copy-text' title='Copy text' href='#'>{total_turn_num}</a></b>{note_html}")
        skills_table.add_cell(f"<b><a id='copy-text' title='Copy text' href='#'>{total_turn_num}</a></b>", width="10px")

        num_skills = len([skill for skill in turn.skills if skill.shorthand not in NON_SKILLS])
        total_skills += num_skills
        total_difficulty += turn.difficulty
        total_flips += turn.total_flips

        cell_value = " ".join(skill.shorthand for skill in turn.skills)
        cell_value = cell_value.replace("X", "<span class=\"x\">X</span>")
        next_line = f"<b>Skills:</b> {num_skills} - <b>Flips:</b> {turn.total_flips} - <b>DD:</b> {turn.difficulty:0.1f}"
        totals_line = f"<b>Skills:</b> {total_skills} - <b>Flips:</b> {total_flips} - <b>DD:</b> {total_difficulty:0.1f}"
        #skills_table.add_cell(f"{cell_value}")
        #skills_table.add_cell(f"<u><b>Turn:</b></u> {next_line}<br><b><u>Total:</u></b> {totals_line}", colspan=most_cols)
        #skills_table.end_row()

        # Add hidden row
        #skills_table.new_row()
        #skills_table.add_cell(f"<b><a id='copy-text' title='Copy text' href='#'>{total_turn_num}</a></b>{note_html}")
        #skills_table.add_cell(f'<i class="expand-turn fa fa-caret-down"></i>{cell_value}{note_html}<br><div style="display: none"><u><b>Turn:</b></u> {next_line}<br><b><u>Total:</u></b> {totals_line}</div>', colspan=most_cols)
        skills_table.add_cell(f'<i class="expand-turn fa fa-plus"></i>{cell_value}{note_html}<br><div style="display: none"><u><b>Turn:</b></u> {next_line}<br><b><u>Total:</u></b> {totals_line}</div>', colspan=most_cols)
        skills_table.end_row()
    skills_table.new_row()
    skills_table.add_cell(totals_line, colspan=most_cols+8, align="center")
    skills_table.end_row()
    skills_table.end_table()
    return skills_table.render()


def update_cache(key, value):
    """Updates the cache"""
    global CACHE
    CACHE[key] = value