from collections import defaultdict
import datetime

from application.utils.utils import NON_SKILLS, is_routine


class Challenge:
    def __init__(self, name, complete_fn):
        self.name = name
        self.complete_fn = complete_fn


def get_starting_date(num_days):
    """
    Returns the starting date for the challenge
    """
    # X days ago
    #return datetime.date.today() - datetime.timedelta(days=num_days)
    
    # Since Sunday
    today = datetime.date.today()
    if today.weekday() == 6:  # Sunday
        return today
    else:
        days_since_sunday = today.weekday() + 1  # Adjust for Monday being 1, ..., Sunday being 7
        most_recent_sunday = today - datetime.timedelta(days=days_since_sunday)
        return most_recent_sunday
    #today = datetime.date.today()
    #return today - datetime.timedelta(days=today.weekday()+1)

def get_next_sunday():
    """
    Returns the date of the next Sunday
    """
    today = datetime.date.today()
    if today.weekday() == 6: # Sunday
        return today + datetime.timedelta(days=7)
    return today + datetime.timedelta(days=6-today.weekday())




# Complete functions
#  determine if a challenge is complete
def finished_a_routine(user_turns, _, num_days=7):
    """
    check if the user finished a routine in the last week
    
    user_turns: [(skill_num, skills, date, user, event, note)]
    """
    starting_date = get_starting_date(num_days)
    for turn in user_turns:
        if turn[2].date() < starting_date:
            continue
        if turn[4] == "trampoline":
            if is_routine(turn[1]):
                return True, turn[2].date()
    
    return False, None


def finished_X_routines(user_turns, _, num_days=7, threshold=1):
    """
    Check if the user finished X routines in the last week
    
    user_turns: [(skill_num, skills, date, user, event, note)]
    """
    starting_date = get_starting_date(num_days)
    routines_completed = 0
    for turn in user_turns:
        if turn[2].date() < starting_date:
            continue
        if turn[4] == "trampoline":
            if is_routine(turn[1]):
                routines_completed += 1
        if routines_completed == threshold:
            return True, turn[2].date()

    return False, None



def airtime_higher_than_X(_, airtimes, num_days=7, threshold=20):
    """
    Check if the airtime is higher than the threshold
    """
    starting_date = get_starting_date(num_days)
    for airtime in airtimes:
        if airtime['date'] < starting_date:
            continue
        try:
            if float(airtime['airtime']) > threshold:
                return True, airtime['date']
        except:
            pass
    
    return False, None


def airtime_higher_than_20(_, airtimes, num_days=7):
    """
    Check if airtimes > 20
    """
    return airtime_higher_than_X(_, airtimes, num_days=num_days, threshold=20)
   

def logged_x_days(user_turns, _, num_days=7, num_logs=1):
    """
    Logged X number of days
    """
    starting_date = get_starting_date(num_days)
    days_logged = set()
    for turn in user_turns:
        if turn[2].date() < starting_date:
            continue
        days_logged.add(str(turn[2].date()))
        if len(days_logged) >= num_logs:
            return True, turn[2].date()
    return False, None


def logged_x_turns_in_a_day(user_turns, _, num_days=7, num_logs=1):
    """
    Logged X times in a day
    """
    starting_date = get_starting_date(num_days)
    days_logged = defaultdict(int)
    for turn in user_turns:
        if turn[2].date() < starting_date:
            continue
        date_str = str(turn[2].date())
        days_logged[date_str] += 1
        if days_logged[date_str] >= num_logs:
            return True, turn[2].date()
    return False, None


# list of this week's challenges
CHALLENGES = [
    Challenge("Log at least one day", lambda user_turns, airtimes: logged_x_days(user_turns, airtimes, num_logs=1)),
    Challenge("Log at least two days", lambda user_turns, airtimes: logged_x_days(user_turns, airtimes, num_logs=2)),
    Challenge("Log at least 10 turns in a practice", lambda user_turns, airtimes: logged_x_turns_in_a_day(user_turns, airtimes, num_logs=10)),
    #Challenge("Finish a trampoline routine", finished_a_routine),
    Challenge("Finish a trampoline routine", lambda user_turns, airtimes: finished_X_routines(user_turns, airtimes, threshold=1)),
    Challenge("Finish two trampoline routines", lambda user_turns, airtimes: finished_X_routines(user_turns, airtimes, threshold=2)),
    #Challenge("Get an airtime higher than 20.00", airtime_higher_than_20)
    Challenge("Get an airtime higher than 20.00", lambda user_turns, airtimes: airtime_higher_than_X(user_turns, airtimes, threshold=20))
]