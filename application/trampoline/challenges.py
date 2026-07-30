from collections import defaultdict
import datetime
import threading

from application.trampoline.trampoline import Athlete
from application.utils.utils import NON_SKILLS, is_routine


class Challenge:
    def __init__(self, name, complete_fn):
        self.name = name
        self.complete_fn = complete_fn


def get_starting_date(num_days, log_date=None):
    """
    Returns the starting date for the challenge
    """
    # X days ago
    #return datetime.date.today() - datetime.timedelta(days=num_days)
    
    # Since Sunday
    today = log_date or datetime.date.today()
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
    return get_sunday(today)
    '''
    if today.weekday() == 6: # Sunday
        return today + datetime.timedelta(days=7)
    return today + datetime.timedelta(days=6-today.weekday())
    '''

def get_sunday(date):
    """
    Returns the sunday before the date
    """
    if date.weekday() == 6: # Sunday
        return date + datetime.timedelta(days=7)
    return date + datetime.timedelta(days=6-date.weekday())


# Complete functions
#  determine if a challenge is complete
def finished_a_routine(user_turns, _, num_days=7, start_date=None):
    """
    check if the user finished a routine in the last week
    
    user_turns: [(skill_num, skills, date, user, event, note)]
    """
    starting_date = start_date or get_starting_date(num_days)
    end_date = starting_date + datetime.timedelta(days=7)
    for turn in user_turns:
        if turn[2].date() < starting_date or turn[2].date() >= end_date:
            continue
        if turn[4] == "trampoline":
            if is_routine(turn[1]):
                return True, turn[2].date()
    
    return False, None


def finished_X_routines(user_turns, _, num_days=7, threshold=1, start_date=None):
    """
    Check if the user finished X routines in the last week
    
    user_turns: [(skill_num, skills, date, user, event, note)]
    """
    starting_date = start_date or get_starting_date(num_days)
    end_date = starting_date + datetime.timedelta(days=7)
    routines_completed = 0
    for turn in user_turns:
        if turn[2].date() < starting_date or turn[2].date() >= end_date:
            continue
        if turn[4] == "trampoline":
            if is_routine(turn[1]):
                routines_completed += 1
        if routines_completed == threshold:
            return True, turn[2].date()

    return False, None



def airtime_higher_than_X(_, airtimes, num_days=7, threshold=20, start_date=None):
    """
    Check if the airtime is higher than the threshold
    """
    starting_date = start_date or get_starting_date(num_days)
    end_date = starting_date + datetime.timedelta(days=7)
    for airtime in airtimes:
        if airtime['date'] < starting_date or airtime['date'] >= end_date:
            continue
        try:
            if float(airtime['airtime']) > threshold:
                return True, airtime['date']
        except:
            pass
    
    return False, None


def airtime_higher_than_20(_, airtimes, num_days=7, start_date=None):
    """
    Check if airtimes > 20
    """
    return airtime_higher_than_X(_, airtimes, num_days=num_days, threshold=20, start_date=start_date)
   

def logged_x_days(user_turns, _, num_days=7, num_logs=1, start_date=None):
    """
    Logged X number of days
    """
    starting_date = start_date or get_starting_date(num_days)
    end_date = starting_date + datetime.timedelta(days=7)
    days_logged = set()
    for turn in user_turns:
        if turn[2].date() < starting_date or turn[2].date() >= end_date:
            continue
        days_logged.add(str(turn[2].date()))
        if len(days_logged) >= num_logs:
            return True, turn[2].date()
    return False, None


def logged_x_turns_in_a_day(user_turns, _, num_days=7, num_logs=1, start_date=None):
    """
    Logged X times in a day
    """
    starting_date = start_date or get_starting_date(num_days)
    end_date = starting_date + datetime.timedelta(days=7)
    days_logged = defaultdict(int)
    for turn in user_turns:
        if turn[2].date() < starting_date or turn[2].date() >= end_date:
            continue
        date_str = str(turn[2].date())
        days_logged[date_str] += 1
        if days_logged[date_str] >= num_logs:
            return True, turn[2].date()
    return False, None



# save completed challenges to DB
def save_in_background(username, challenges, start_date=None):
    """
    Saves the completed challenges in the background
    """
    thread = threading.Thread(
        target=save_completed_challenges,
        args=(username, challenges, start_date,)
    )
    thread.start()


def save_completed_challenges(username, challenges, start_date=None):
    """
    Save the completed challenges to the DB (in the background)

    challenges: {'challenge': (True/False, date), ...}
    """
    athlete = Athlete.load(username)
    completed = athlete.details.get('completed_challenges', {})

    if not start_date:
        next_sunday = get_next_sunday()
        challenge_date_start = next_sunday - datetime.timedelta(days=7)
    else:
        challenge_date_start = start_date
        next_sunday = challenge_date_start + datetime.timedelta(days=7)
    title = f"{challenge_date_start.strftime('%Y/%m/%d')} - {next_sunday.strftime('%Y/%m/%d')}"
    weekly_challenges = {
        title: [
            f"{challenge} ({info[1]})"
            for challenge, info in challenges.items()
            if info[0]
        ]
    }
    completed.update(weekly_challenges)
    athlete.details['completed_challenges'] = completed
    athlete.save()


# list of this week's challenges
CHALLENGES = [
    Challenge("Log at least one day", lambda user_turns, airtimes, **kwargs: logged_x_days(user_turns, airtimes, num_logs=1, **kwargs)),
    Challenge("Log at least two days", lambda user_turns, airtimes, **kwargs: logged_x_days(user_turns, airtimes, num_logs=2, **kwargs)),
    Challenge("Log at least 10 turns in a practice", lambda user_turns, airtimes, **kwargs: logged_x_turns_in_a_day(user_turns, airtimes, num_logs=10, **kwargs)),
    #Challenge("Finish a trampoline routine", finished_a_routine),
    Challenge("Finish a trampoline routine", lambda user_turns, airtimes, **kwargs: finished_X_routines(user_turns, airtimes, threshold=1, **kwargs)),
    Challenge("Finish two trampoline routines", lambda user_turns, airtimes, **kwargs: finished_X_routines(user_turns, airtimes, threshold=2, **kwargs)),
    #Challenge("Get an airtime higher than 20.00", airtime_higher_than_20)
    Challenge("Get an airtime higher than 20.00", lambda user_turns, airtimes, **kwargs: airtime_higher_than_X(user_turns, airtimes, threshold=20, **kwargs))
]

def retroactively_save_in_bg(username, user_turns, airtimes):
    """
    Saves the challenges in the db in the background
    """
    thread = threading.Thread(
        target=retroactively_record_challenges,
        args=(username, user_turns, airtimes,)
    )
    thread.start()

def retroactively_record_challenges(username, user_turns, airtimes):
    """
    Save all challenges into the user since their first log
    """
    completed_challenges = {}
    sorted_user_turns = sorted(user_turns, key=lambda x: x[2])
    sorted_airtimes = sorted(airtimes, key=lambda x: x['date'])

    # split data into bins of weeks
    turn_weeks = get_week_bins(user_turns)
    airtime_weeks = get_week_bins(airtimes)
    print(airtime_weeks)

    weeks = {
        week['week']: {'turns': week['data']}
        for week in turn_weeks
    }
    for week in airtime_weeks:
        if week['week'] in weeks:
            weeks[week['week']]['airtimes'] = week['data']
        else:
            weeks[week['week']] = {'airtimes': week['data']}

    for week, week_data in weeks.items():
        week = week if type(week) == datetime.date else week.date()
        weekly_completed = {}
        for challenge in CHALLENGES:
            completed = challenge.complete_fn(week_data.get('turns', []), week_data.get('airtimes', []), start_date=week)
            print(f"week: {week} - completed: {completed} - challenge: {challenge.name}")
            if completed[0]:
                weekly_completed[challenge.name] = completed
        if weekly_completed:
            save_completed_challenges(username, weekly_completed, start_date=week)
        #save_in_background(username, completed_challenges[week], start_date=week)
        completed_challenges[week] = weekly_completed

    print(completed_challenges)


def get_week_bins(data):
    """
    Aggregate data into weekly bins starting from Sunday to Saturday.
    """
    # Sort the data based on the date
    sorted_data = sorted(data, key=lambda x: x[2])
    
    # Initialize variables
    current_week_start = get_sunday(sorted_data[0][2]) - datetime.timedelta(days=7)
    current_week_data = []
    weeks = []

    # Iterate through the sorted data
    for point in sorted_data:
        date = point[2]
        print(f"week start: {current_week_start}. date: {date}")
        # Check if the point is within the current week
        if date < current_week_start + datetime.timedelta(weeks=1):
            current_week_data.append(point)
        else:
            # If the point falls into the next week, store the current week's data
            weeks.append({'week': current_week_start, 'data': current_week_data})
            # Move to the next week
            current_week_start += datetime.timedelta(weeks=1)
            current_week_start = get_sunday(point[2]) - datetime.timedelta(days=7)
            current_week_data = [point]

    # Store the data of the last week
    weeks.append({'week': current_week_start, 'data': current_week_data})
    
    return weeks
