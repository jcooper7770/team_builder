NON_SKILLS = [
    "X", "..."
]


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
            'class="table table-striped"'
        ]
        if self.width:
            options.append(f"width='{self.width}'")
        options_str = " ".join(options)
        self.table.append('<div class="container">')
        self.table.append(f"<table {options_str}>")
        self.table.append("<thead class=\"thead-dark\">")
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
            self.table.append(f'<th colspan={colspan} align="center">{value}<button type="button" class="btn float-right"><a title="remove day" href="/logger/delete/{date_to_remove}/{event_to_remove}"><span class="fa fa-remove" aria-hidden=\'true\'></span></a></button></th>')
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


def create_table_from_results(results, pokemon=None, width=None, tc=None, tooltip=True):
    """
    Creates an html table from the results.
    Results are in the form:
    value
    value    value    value    value
    value    value    value    value
    value    value    value    value

    :param results: The results
    :type results: str
    :param pokemon: The pokemon to simulatem battles for (Default: None)
    :type pokemon: str

    :return: the table for the results
    :rtype: str
    """
    table = TableMaker(border=1, align="center", bgcolor="#FFFFFF", width=width)

    for line in results.split("\n"):
        if not line:
            continue
        table.new_row()

        # If a single value in a line then create a new table
        values = line.split("\t")
        if len(values) == 0:
            table.end_row()
            table.end_table()
        elif len(values) == 1:
            table.reset_table()
            table.add_cell(values[0], colspan=4, align="center")
        else:
            for value in values:
                if value:
                    # Provide links to battles
                    if pokemon and ':' in value:
                        league_val = LEAGUE_VALUE.get(CACHE.get('league', ''), '1500')
                        cell_pokemon = value.split(':')[0].strip()

                        # make pvpoke link
                        pvpoke_link = f"https://pvpoke.com/battle/{league_val}/{cell_pokemon}/{pokemon}/11"

                        # simulate battle for text color
                        try:
                            winner, leftover_health, battle_text = sim_battle(cell_pokemon, pokemon, tc)
                            tool_tip_text = "&#013;&#010;</br>".join(battle_text)
                            #logger.info(f"winner: {winner} - leftover_health: {leftover_health}")
                        except Exception as exc:
                            winner = None
                            logger.error(f"{cell_pokemon}")
                            logger.error(traceback.format_exc())
                            leftover_health = 0
                            tool_tip_text=  ""
    
                        if winner == pokemon:
                            text_color = "#00FF00"
                            text_color = "#%02x%02x%02x" % (0, 100 + int(155 * leftover_health), 0)
                        elif winner == cell_pokemon:
                            text_color = "#FF0000"
                            text_color = "#%02x%02x%02x" % (100 + int(155 * leftover_health), 0, 0)
                        else:
                            text_color = "#000000"
                        #logger.info(f"{cell_pokemon}: {text_color}")
                        tooltip_addition = f"<span class='tooltiptext'>{tool_tip_text}</span>" if tooltip else ""
                        value = f"<a class='tooltip' href='{pvpoke_link}' style='color: {text_color}; text-decoration: none;' target='_blank'>{value}{tooltip_addition}</a>"
                    table.add_cell(value)

        table.end_row()

    table.end_table()
    return table.render()


def skills_table(skills, title="Routines"):
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
        if turn.note:
            skills_table.add_cell(turn.note, colspan=most_cols+8)
            continue
        total_turn_num += 1
        # Turn number (also a link to copy the turn)
        routine_str = ' '.join(skill.shorthand for skill in turn.skills)
        skills_table.add_cell(f"<b><a title='Copy text' href='/logger?routine={routine_str}'>{total_turn_num}</a></b>")

        # Skills
        for skill in turn.skills:
            skills_table.add_cell(skill.shorthand)
        # metrics
        skills_table.add_cell("")
        for _ in range(most_cols - len(turn.skills)):
            skills_table.add_cell("")

        # total skills
        num_skills = len([skill for skill in turn.skills if skill.shorthand not in NON_SKILLS])
        skills_table.add_cell(num_skills)
        total_skills += num_skills
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
