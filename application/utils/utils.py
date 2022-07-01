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
    "X", "..."
]
CACHE = {'results': {}, 'team_maker': {}, 'num_days': 1, 'rating': None}

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
            'class="table table-striped table-responsive-lg"'
        ]
        if self.width:
            options.append(f"width='{self.width}'")
        options_str = " ".join(options)
        self.table.append('<div class="container">')
        self.table.append(f"<table {options_str}>")
        self.table.append("<thead class=\"thead-dark bg-dark text-white\">")
        self._row_num = 0

    def end_table(self):
        self.table.append("</tbody></table></div>")
        self._row_num = 0

    def new_row(self):           
        self.table.append("<tr>")
        self._row_num += 1

    def end_row(self):
        self.table.append("</tr>")
        if self._row_num == 1:
            self.table.append("</thead><tbody>")

    def new_line(self):
        self.table.append("<br>")

    def new_header(self, value, colspan):
        self.new_row()
        try:
            date_to_remove = value.split()[1].replace("/", '-')
            event_to_remove = value.split()[2].replace("(", "").replace(")", "")
            self.table.append(f'<th colspan={colspan} align="center">{value}<button type="button" class="btn float-right"><a title="remove day" href="#"><span id="remove_{date_to_remove}_{event_to_remove}" class="fa fa-remove" aria-hidden=\'true\'></span></button></th>')
        except:
            self.table.append(f'<th colspan={colspan} align="center">{value}</th>')
        self.end_row()

    def reset_table(self):
        if not self.first_table:
            self.end_row()
            self.end_table()
            self.new_line()
            self.new_table()
            self.new_row()
            
        self.first_table = False

    def add_cell(self, value, colspan=None, align=None, width=None):
        colspan_text = f" colspan={colspan}" if colspan else ""
        align_text = f" align='{align}'" if align else ""
        width_text = f" width='{width}'" if width else ""
        self.table.append(f"<td{colspan_text}{align_text}{width_text}>{value}</td>")

    def render(self):
        return "".join(self.table)


def skills_table(skills, title="Routines", expand_comments=False):
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
    skills_table.new_header(title, colspan=most_cols+8)
    total_turn_num = 0
    
    for turn_num, turn in enumerate(skills):
        skills_table.new_row()
        if turn.note and not turn.skills:
            cell = f'<i class="fa fa-comments"></i> {turn.note}'
            skills_table.add_cell(cell, colspan=most_cols+8)
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
            note_html = f' <i title="toggle comment" class="fa fa-comments" id="unhide-note"></i> <span id="hidden-note" style="display:{display};">{turn.note}</span>'
        skills_table.add_cell(f"<b><a id='copy-text' title='Copy text' href='#'>{total_turn_num}</a></b>{note_html}")

        # Skills
        for skill in turn.skills:
            skills_table.add_cell(skill.shorthand)
        
        # put all skills in a single cell instead?
        #skills_table.add_cell(" ".join([skill.shorthand for skill in turn.skills]))

        # metrics
        skills_table.add_cell("")
        for _ in range(most_cols - len(turn.skills)):
            skills_table.add_cell("")

        # total skills
        num_skills = len([skill for skill in turn.skills if skill.shorthand not in NON_SKILLS])
        #skills_table.add_cell(num_skills, colspan="1 style=\"border-left: 1px solid black;\"")
        skills_table.add_cell(num_skills)
        total_skills += num_skills
        #skills_table.add_cell(total_skills, colspan="1 style=\"border-left: 1px solid black;\"")
        skills_table.add_cell(total_skills)

        # total flips
        skills_table.add_cell(turn.total_flips)
        total_flips += turn.total_flips
        skills_table.add_cell(total_flips)

        # total difficulty
        skills_table.add_cell(f"{turn.difficulty:0.1f}")
        total_difficulty += turn.difficulty
        skills_table.add_cell(f"{total_difficulty:0.1f}")

        skills_table.end_row()
    skills_table.end_table()
    return skills_table.render()
