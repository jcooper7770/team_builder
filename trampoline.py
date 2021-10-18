"""
Utilities for trampoline app

TODO:
  - incorporate '...' (stop in middle of turn)
  - add in 'X' for bail during turn
  - Log in with different users so multiple people can use the logger
  - Add in notes for a practice or a turn
  - Add in double mini
"""

import datetime
import json
import os


NUM_FLIPS = {
    2: 1,
    3: 2,
    5: 3,
    6: 4
}


class Practice:
    """
    All turns/skills done in a practice
    """
    def __init__(self, practice_date, turns):
        self.date = practice_date
        self.turns = turns

    def save(self):
        """
        Save the current practice
        """
        file_name = os.path.join("practices", f"{self.date.strftime('%Y%m%d')}.txt")
        current_day = {
            str(self.date): {
                'turns': []
            }
        }
        if not os.path.isdir("practices"):
            os.mkdir("practices")
    
        if os.path.exists(file_name):
            with open(file_name) as practice_file:
                current_day = json.load(practice_file)

        with open(file_name, 'w') as practice_file:
            current_day[str(self.date)]['turns'].extend([turn.toJSON() for turn in self.turns])
            json.dump(current_day, practice_file)

        return current_day

    @classmethod
    def load(self, practice_data):
        """
        Loads in a practice
        """
        date = list(practice_data.keys())[0]
        return Practice(
            datetime.datetime.strptime(date, '%Y-%m-%d').date(),
            [Routine([Skill(skill) for skill in routine]) for routine in practice_data[date]['turns']]
        )


class Skill:
    """
    A skill converted from a string
    """
    def __init__(self, string):
        self.flips = 0
        self.twists = []
        self.pos = string[-1]
        self.shorthand = string

        self.flips = float(string[:-(NUM_FLIPS[len(string[:-1])]+1)])/4.0
        self.twists = [int(n)/2.0 for n in string[len(str(int(self.flips*4))):-1]]
        self.difficulty = get_skill_difficulty(self)

    def __str__(self):
        return f"{self.flips} flips - {self.twists} twists - {self.pos} position ({self.difficulty:0.1f})"

    def __repr__(self):
        return str(self)


class Routine():
    """
    Routine
    """
    def __init__(self, skills):
        self.skills = skills
        self.total_flips = sum([skill.flips for skill in self.skills])
        self.total_twists = sum([sum(skill.twists) for skill in self.skills])
        self.difficulty = sum([skill.difficulty for skill in self.skills])

    def __str__(self):
        return f'{self.total_flips} flips - {self.total_twists} twists ({self.difficulty:0.1f})'

    def __repr__(self):
        return str(self)

    def toJSON(self):
        return [skill.shorthand for skill in self.skills]


def get_skill_difficulty(skill):
    """
    Returns the difficulty/tarrif of the skill
    """
    difficulty_per_flip = 0.5 if skill.pos in ['o', 't'] else 0.6
    flip_difficulty = (skill.flips - skill.flips%1) * difficulty_per_flip + \
                      (skill.flips % 1 / 0.25) * 0.1
    
    return flip_difficulty \
           + sum([2*twist for twist in skill.twists]) * 0.1 \
           + (0.1 if skill.flips == 3 else 0) # extra 0.1 for a triple flip


def convert_form_data(form_data, logger=print):
    """
    Converts the data from the form into trampoline routines
    and returns a list of Routine objs
    """
    if not form_data:
        return []
    # Split by spaces for each skill
    #turns = form_data.split('\r\n')
    turns = form_data.splitlines()
    turn_skills = [turn.split(' ') for turn in turns]
    logger(f"turn_skills: {turn_skills}")

    skill_turns = []
    for turn in turn_skills:
        skills = []
        if not turn:
            continue
        for skill in turn:
            try:
                skills.append(Skill(skill))
            except:
                continue
        routine = Routine(skills)
        skill_turns.append(routine)
        #skill_turns.append(skills)
    return skill_turns


def pretty_print(routine, logger=print):
    """
    Prety print the routine
    """
    for turn_num, turn in enumerate(routine):
        logger(f"{turn_num}:")
        for skill in turn.skills:
            logger(f"\t{skill}")
        logger(turn)


if __name__ == '__main__':
    pretty_print(convert_form_data('12001o 811< 803< 40/'))
    print()
    routines = convert_form_data('11000o 800o 901o 40o 40/ 40< 41o 800o 801o 822o')
    pretty_print(routines)

    routines = convert_form_data('12001< 811< 12001o 822/ 823/ 811o 821< 831< 801< 833/')
    pretty_print(routines)

    routines = convert_form_data('12001< 811< 12001o 811o 803< 813o 803o 800< 801< 813<')
    pretty_print(routines)

