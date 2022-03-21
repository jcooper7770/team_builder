"""
Utilities for trampoline app

TODO:
  - [DONE] incorporate '...' (stop in middle of turn)
  - [DONE] add in 'X' for bail during turn
  - Log in with different users so multiple people can use the logger
  - [DONE] Add in notes for a practice or a turn
  - [DONE] Add in double mini
  - Update difficulty for double mini
  - Add about page on shortcuts
  - Save in a database instead of text files
  - [DONE] Add athlete compulsory and optional
"""

import datetime
import json
import os
import re

from collections import defaultdict


NUM_FLIPS = {
    1: 0,
    2: 1,
    3: 2,
    5: 3,
    6: 4
}

CURRENT_USER = "bob"
CURRENT_ATHLETE = None
EVENT = "trampoline"
NON_SKILLS = [
    "X", "..."
]

COMMON_ROUTINES = defaultdict(str, {
    "twisting swingtime": "40o 41o 42/ 41< 40< 43/ 40/ 41/ 44/",
    "swingtime": "40o 41o 40< 41< 40/ 41/",
    "three halfouts": "801< 40/ 801o 40/ 803<"
})

SKILLS = [
    # Singles
    "40", "41", "42", "43", "44", "45",
    # Doubles
    "800", "801", "802", "803", "805",
    "811", "813", "815",
    "822", "823", "824", "825", "826",
    "831", "833", "835",
    # Triples
    "12000", "12001", "12003",
    "12101", "12103",
    "12200", "12222"
]
POSITIONS = ["o", "<", "/"]


class Athlete:
    """
    Information about athlete
    """
    def __init__(self, name):
        self.name = name
        self.compulsory = []
        self.optional = []

    def set_comp(self, skills):
        """
        Sets the athlete's compulsory
        """
        self.compulsory = skills
        self.save()

    def set_opt(self, skills):
        """
        Sets the athlete's optional
        """
        self.optional = skills
        self.save()

    def save(self):
        """
        Saves the athlete into the database
        """
        file_name = os.path.join("athletes", f'{self.name}.json')
        if not os.path.isdir("athletes"):
            os.mkdir("athletes")

        athlete_data = {
            'name': self.name,
            'compulsory': self.compulsory,
            'optional': self.optional
        }
        with open(file_name, 'w') as athlete_file:
            json.dump(athlete_data, athlete_file)

    @classmethod
    def load(self, name):
        """
        Loads in an athlete
        """
        file_path = os.path.join("athletes", f'{name}.json')

        if not os.path.exists(file_path):
            return Athlete(name)

        with open(file_path) as athlete_file:
            athlete_data = json.load(athlete_file)
            athlete = Athlete(athlete_data['name'])
            athlete.compulsory = athlete_data['compulsory']
            athlete.optional = athlete_data['optional']
            return athlete


class Practice:
    """
    All turns/skills done in a practice
    """
    def __init__(self, practice_date, turns, event):
        self.date = practice_date
        self.turns = turns
        self.event = event

    def save(self):
        """
        Save the current practice
        """
        user_dir = os.path.join("practices", CURRENT_USER)
        file_name = os.path.join(user_dir, f"{self.date.strftime('%Y%m%d')}_{self.event}.txt")
        current_day = {
            str(self.date): {
                'turns': []
            }
        }
        if not os.path.isdir(user_dir):
            os.mkdir(user_dir)
    
        if os.path.exists(file_name):
            with open(file_name) as practice_file:
                current_day = json.load(practice_file)

        with open(file_name, 'w') as practice_file:
            current_day[str(self.date)]['turns'].extend([turn.toJSON() for turn in self.turns])
            json.dump(current_day, practice_file)

        # Save the athlete also
        athlete = Athlete.load(CURRENT_USER)
        athlete.save()

        return current_day

    @classmethod
    def load(self, practice_data, event):
        """
        Loads in a practice
        """
        date = list(practice_data.keys())[0]
        return Practice(
            datetime.datetime.strptime(date, '%Y-%m-%d').date(),
            [Routine([Skill(skill) for skill in routine]) if (routine and routine[0][0]!="-") else Routine([], note=routine[0][1:] if routine else routine) for routine in practice_data[date]['turns']],
            event
        )

    @classmethod
    def delete(self, practice_date):
        """
        Deletes the practice from the given day
        """
        deleted = False
        user_dir = os.path.join("practices", CURRENT_USER)
        for _, _, practice_files in os.walk(user_dir):
            print(f"files: {practice_files}")
            for practice_file in practice_files:
                if practice_file.startswith(f"{practice_date.strftime('%Y%m%d')}"):
                    file_name = os.path.join(user_dir, practice_file)
                    os.remove(file_name)
                    deleted = True
        return deleted
        

class Skill:
    """
    A skill converted from a string
    """
    def __init__(self, string):
        self.flips = 0
        self.twists = []
        self.pos = string[-1]
        self.shorthand = string

        if string not in NON_SKILLS:
            self.flips = float(string[:-(NUM_FLIPS[len(string[:-1])]+1)])/4.0
            self.twists = [int(n)/2.0 for n in string[len(str(int(self.flips*4))):-1]]
            self.difficulty = get_skill_difficulty(self)
        else:
            self.flips, self.twists, self.difficulty = (0, [0], 0)

    def __str__(self):
        return f"{self.shorthand} - {self.flips} flips - {self.twists} twists - {self.pos} position ({self.difficulty:0.1f})"

    def __repr__(self):
        return str(self)


class Routine():
    """
    Routine
    """
    def __init__(self, skills, event=EVENT, note=None):
        self.skills = skills
        self.event = event
        self.note = note
        self.total_flips = sum([skill.flips for skill in self.skills])
        self.total_twists = sum([sum(skill.twists) for skill in self.skills])
        self.difficulty = sum([skill.difficulty for skill in self.skills])

    def __str__(self):
        return f'{self.total_flips} flips - {self.total_twists} twists ({self.difficulty:0.1f})'

    def __repr__(self):
        return str(self)

    def toJSON(self):
        if self.skills:
            return [skill.shorthand for skill in self.skills]
        return [self.note]


def current_user():
    """
    Returns the current user
    """
    return CURRENT_USER


def set_current_user(user):
    """
    Sets the current user
    """
    global CURRENT_USER
    CURRENT_USER = user

def current_event():
    """
    Returns the current event
    """
    return EVENT


def set_current_event(event):
    """
    Sets the current event
    """
    global EVENT
    EVENT = event

def set_current_athlete(name):
    """
    Sets the current athlete
    """
    global CURRENT_ATHLETE
    CURRENT_ATHLETE = Athlete.load(name)


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


def convert_form_data(form_data, logger=print, event=EVENT):
    """
    Converts the data from the form into trampoline routines
    and returns a list of Routine objs
    """
    athlete = Athlete.load(CURRENT_USER)
    logger(f"Comp: {athlete.compulsory}")
    logger(f"opt: {athlete.optional}")

    if not form_data:
        return []

    # Replace any thing inside of a parentethese
    #  i.e. (40o 41o)x2 -> 40o 41o 40o 41o
    matches = re.findall("(\((.[^x]*)\)x([0-9]*))", form_data)
    for match in matches:
        form_data = form_data.replace(
            # Takes the entire string
            match[0],
            # and replaces it with the correct number of what is inside the parentethese
            ' '.join([match[1]]*int(match[2]))
        )

    # Replace common routines
    for common_name, common_routine in COMMON_ROUTINES.items():
        form_data = form_data.replace(common_name, common_routine)

    # Replace compulsory or optional
    form_data = form_data.replace('compulsory', ' '.join(athlete.compulsory))
    form_data = form_data.replace('optional', ' '.join(athlete.optional))
    
    # Split by spaces for each skill
    #turns = form_data.split('\r\n')
    turns = form_data.splitlines()
    turn_skills = [turn.split(' ') for turn in turns]
    logger(f"turn_skills: {turn_skills}")

    skill_turns = []
    for turn in turn_skills:
        # notes start with '-'
        if turn[0] == '-':
            routine = Routine([], event=event, note=' '.join(turn[1:]))
            skill_turns.append(routine)
            continue
            
        skills = []
        if not turn:
            continue
        # Set athlete compulsory or optional
        if turn[0] == 'comp:':
            athlete.set_comp(turn[1:])
        elif turn[0] == 'opt:':
            athlete.set_opt(turn[1:])

        for skill in turn:
            try:
                skills.append(Skill(skill))
            except:
                repeats = re.findall("x([0-9]*)", skill)
                if repeats:
                    for _ in range(int(repeats[0]) - 1):
                        skills.append(skills[-1])
                else:
                    logger(f"Cannot convert '{skill}' into a skill")
                continue
        routine = Routine(skills, event=event)
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

    routines = convert_form_data('40o X 40o 41o ... 822/')
    pretty_print(routines)

    routines = convert_form_data('swingtime 822/')
    pretty_print(routines)

    routines = convert_form_data('(swingtime)x3 822/')
    pretty_print(routines)

