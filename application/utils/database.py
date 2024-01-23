"""
Database operations
"""


from ast import Return
import sqlalchemy

from application.utils.mock_database import MockEngine2, MockTable2

import json
import os
import datetime
import random


ENGINE = None
DB_TABLE = None
TABLE_NAME = "test_data"
TABLE_NAME = "test_data" if os.environ.get("FLASK_ENV", "prod") == "prod" else "test_db"
print(f"Using table: {TABLE_NAME}")

class MockEngine(sqlalchemy.engine.Engine):
    """
    Mock engine for offline development
    """
    def __init__(self):
        pass

    def execute(self, query):
        class MockResult(list):
            rowcount = 0
            def close(self):
                return
            
            def __next__(self):
                raise StopIteration()

        return MockResult()

    def connect(self):
        class MockConnect:
            def close(self):
                return

        return MockConnect()

    def dispose(self):
        return


class MockTable:
    def insert(self):
        class MockInsert:
            def values(self, *args, **kwargs):
                return
        return MockInsert()


def set_table_name(table_name):
    global TABLE_NAME
    TABLE_NAME = table_name


def create_engine(table_name=None, timeout=60):
    table_name = table_name or TABLE_NAME
    global ENGINE
    global DB_TABLE
    url = "itsflippincoop.com" if table_name == "test_data" else "127.0.0.1"
    mock_data = True if os.environ.get("MOCK_DATA", "prod") == "test" else False
    if mock_data:
        print("~Using mock data~")
        DB_TABLE = MockTable2()
        return MockEngine2()

    db_name = "tramp" if os.environ.get("FLASK_ENV", "prod") == "prod" else "test_tramp"
    print(f"Using db: {db_name}")
    engine = sqlalchemy.create_engine(
        f'mysql+pymysql://itsflippincoop:password@itsflippincoop.com:3306/{db_name}',
        echo=True,
        connect_args={'connect_timeout': timeout},
        pool_recycle=1800
    )
    ENGINE = engine
    metadata = sqlalchemy.MetaData()
    #table = sqlalchemy.Table(table_name, metadata, autoload_with=engine)
    table = sqlalchemy.Table(table_name, metadata, autoload=True, autoload_with=engine)
    try:
        table = sqlalchemy.Table(table_name, metadata, autoload=True, autoload_with=engine)
        DB_TABLE = table
        return engine
    except sqlalchemy.exc.OperationalError:
        DB_TABLE = MockTable()
        return MockEngine()


def get_user(user):
    """
    Returns the user
    """
    engine = create_engine()
    conn = engine.connect()

    # First check if user exists
    result = engine.execute(f'SELECT * from `users` WHERE LOWER(`user`)="{user.lower()}"')
    
    if result.rowcount == 0:
        raise Exception(f"No user in db by name of {user}")

    if os.environ.get("MOCK_DATA", "") == "test":
        print(f"user: {[x for x in result]}. rowcount: {result.rowcount}")

    user = [res for res in result][0]
    print(f"user: {user}")
    result.close()
    conn.close()
    engine.dispose()
    return {
        "name": user[0],
        "private": user[1],
        "compulsory": user[2],
        "optional": user[3],
        "password": user[4],
        "expand_comments": user[5],
        "is_coach": user[6],
        "athletes": json.loads(user[7]),
        "first_login": user[8],
        'signup_date': user[9],
        "messages": json.loads(user[10]),
        'dm_prelim1': user[11],
        'dm_prelim2': user[12],
        'dm_finals1': user[13],
        'dm_finals2': user[14],
        'levels': json.loads(user[15]),
        "coach_requests": json.loads(user[16]),
        'details': json.loads(user[17])
    }


def add_to_db(turns, user, event, practice_date, table=None, tags=[]):
    table = table or TABLE_NAME
    engine = create_engine(table)
    if DB_TABLE is None:
        create_engine(table)
    if isinstance(turns, list):
        for turn_num, turn in enumerate(turns):
            turn_str = ' '.join(turn)
            ins = DB_TABLE.insert().values(
                turn_num=turn_num + 1,
                turn=turn_str,
                event=event,
                user=user,
                date=practice_date,
                tags=','.join(tags)
            )
            engine.execute(ins)
    elif isinstance(turns, dict):
        for turn_num, turn in turns.items():
            turn_str = ' '.join(turn['skills'])
            ins = DB_TABLE.insert().values(
                turn_num=turn_num,
                turn=turn_str,
                event=event,
                user=user,
                date=practice_date,
                note=turn['note'],
                tags=','.join(tags)
            )
            engine.execute(ins)


def add_post_to_db(user, date, post, filename):
    """
    Adds the pose to athlete_posts
    """
    engine = create_engine()
    metadata = sqlalchemy.MetaData()
    try:
        table = sqlalchemy.Table("athlete_posts", metadata, autoload=True, autoload_with=engine)
    except:
        table = MockTable()
    ins = table.insert().values(
        name=user,
        date=date,
        post=post,
        filename=filename
    )
    engine.execute(ins)

def delete_post_from_db(name, date):
    """
    Deletes the post from the database
    """
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("athlete_posts", metadata, autoload=True, autoload_with=ENGINE)
    delete = table.delete().where(table.c.name==name).where(table.c.date==date)
    return ENGINE.execute(delete)


def get_posts_from_db():
    """
    Returns all posts from db
    """
    engine = create_engine()
    result = engine.execute('SELECT * from `athlete_posts`;')
    posts = [post for post in result]
    all_posts = []
    # TODO: sort
    for post in posts:
        all_posts.append({"name": post[0], "date": post[1], "post": post[2], "filename": post[3]})
    return all_posts



def add_airtime_to_db(user, airtime, date_str):
    """
    Add goal to db for user
    """
    engine = create_engine()
    metadata = sqlalchemy.MetaData()
    try:
        table = sqlalchemy.Table("airtimes", metadata, autoload=True, autoload_with=engine)
    except:
        table = MockTable()
    ins = table.insert().values(
        user=user,
        airtime=airtime,
        date=date_str
    )
    engine.execute(ins)


def get_user_airtimes(user):
    """
    Returns the airtimes for the user
    """
    engine = create_engine()
    result = engine.execute(f'SELECT * from `airtimes` WHERE airtimes.user="{user}";')

    airtimes = [airtime for airtime in result]
    print(f"Returned {result.rowcount} airtimes")
    result.close()
    return sorted(airtimes, key=lambda x: x[2], reverse=True)


def delete_airtime_from_db(user, airtime):
    """
    Deletes the airtime
    """
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("airtimes", metadata, autoload=True, autoload_with=ENGINE)
    delete = table.delete().where(table.c.user==user).where(table.c.airtime==airtime['airtime']).where(table.c.date==airtime['date'])
    # Figure out why it is not deleting the entire row in db but just the airtime value
    ENGINE.execute(delete)


def insert_goal_to_db(user, goal):
    """
    Add goal to db for user
    """
    engine = create_engine()
    metadata = sqlalchemy.MetaData()
    try:
        table = sqlalchemy.Table("goals", metadata, autoload=True, autoload_with=engine)
    except:
        table = MockTable()
    ins = table.insert().values(
        user=user,
        goal=goal,
        done=False
    )
    engine.execute(ins)


def complete_goal(user, goal, done=True):
    """
    Completes the goal
    """
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("goals", metadata, autoload=True, autoload_with=ENGINE)
    update = table.update().where(table.c.user==user).where(table.c.goal==goal).values(
        user=user,
        goal=goal,
        done=done
    )
    ENGINE.execute(update)

    
def get_user_goals(user):
    """
    Returns the goals for the user
    """
    engine = create_engine()
    result = engine.execute(f'SELECT * from `goals` WHERE goals.user="{user}";')

    goals = [goal for goal in result]
    print(f"Returned {result.rowcount} goals")
    result.close()
    return sorted(goals, key=lambda x: x[3])


def delete_goal_from_db(user, goal):
    """
    Deletes the goal
    """
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("goals", metadata, autoload=True, autoload_with=ENGINE)
    delete = table.delete().where(table.c.user==user).where(table.c.goal==goal)
    ENGINE.execute(delete)


def get_from_db(table_name=None, user="test", date=None, skills=None, date2=None):
    table_name = table_name or TABLE_NAME
    engine = create_engine(table_name)

    where_clause = [f'LOWER({table_name}.user)="{user}"']

    if not date2:
        date2 = date
    if date:
        where_clause.append(f'{table_name}.date BETWEEN "{date}" AND "{date2}"')
    if skills:
        where_clause.append(f'{table_name}.turn LIKE "%%{skills}%%"')
    query_base = f'SELECT * from `{table_name}`'
    query = f'{query_base} WHERE ({" AND ".join(where_clause)});'
    print(f"query: {query}")

    result = engine.execute(query)
    '''
    if date:
        result = engine.execute(f'SELECT * from `{table_name}` WHERE (LOWER({table_name}.user)="{user.lower()}" AND {table_name}.date="{date}");')
    else:
        result = engine.execute(f'SELECT * from `{table_name}` WHERE LOWER({table_name}.user)="{user.lower()}";')
    '''
    
    mock_turns = [
        [skill_num, '801<', datetime.datetime.now(), user, random.choice(["trampoline", "dmt"])]
        for skill_num in range(10)
    ]
    mock_turns.append([100, '- mock data served', datetime.datetime.now(), user, "trampoline"])
    mock_turns.append([100, '- mock data served', datetime.datetime.now(), user, "dmt"])
    turns = [res for res in result]
    num_results = result.rowcount
    if num_results == 0:
        #turns = mock_turns
        print(f"Got {len(turns)} mock turns")
    else:
        print(f"Got {num_results} turns")
    result.close()
    #return sorted(turns, key=lambda turn: (turn[2], turn[0]))
    return sorted(turns, key=lambda turn: (turn[2]), reverse=True)
    


def delete_from_db(date, user="test", table_name=None, event=None):
    table_name = table_name or TABLE_NAME
    engine = create_engine(table_name)
    date_time = datetime.datetime.combine(date, datetime.datetime.min.time())
    if event:
        result = engine.execute(f'DELETE from `{table_name}` WHERE ({table_name}.user="{user}" AND {table_name}.date="{date}" AND {table_name}.event="{event}");')
    else:
        result = engine.execute(f'DELETE from `{table_name}` WHERE ({table_name}.user="{user}" AND {table_name}.date="{date}");')
    print(f"removed {result.rowcount} rows")


def get_ratings(user):
    """
    Returns all ratings from the db
    """
    engine = create_engine()
    result = engine.execute(f'SELECT * from `ratings` where `user`="{user}";')
    ratings = [rating for rating in result]
    result.close()
    ratings_map = {}
    for rating in ratings:
        ratings_map[rating[0]] = rating[1]

    return ratings_map




def rate_practice_in_db(date, event, rating, user):
    """
    Saves the rating to the database
    """
    practice = f"{date}_{event}"
    engine = create_engine()
    conn = engine.connect()
    metadata = sqlalchemy.MetaData()
    try:
        table = sqlalchemy.Table("ratings", metadata, autoload=True, autoload_with=engine)
    except:
        table = MockTable()
    # First check if user exists
    result = engine.execute(f'SELECT * from `ratings` WHERE `practice`="{practice}" AND `user`="{user}"')
    if result.rowcount == 0:
        # add in rating
        ins = table.insert().values(
            practice=practice,
            rating=rating,
            user=user
        )
        engine.execute(ins)
    else:
        # else update user
        update = table.update().where(table.c.practice==practice).where(table.c.user==user).values(
            rating=rating
        )
        engine.execute(update)
    
    result.close()
    conn.close()
    engine.dispose()
  

def save_athlete(athlete):
    """
    Saves the athlete to the DB
    """
    engine = create_engine()
    conn = engine.connect()
    metadata = sqlalchemy.MetaData()
    try:
        table = sqlalchemy.Table("users", metadata, autoload=True, autoload_with=engine)
    except:
        table = MockTable()
    if os.environ.get("MOCK_DATA") == "test":
        table = MockTable2()
    # First check if user exists
    result = engine.execute(f'SELECT * from `users` WHERE `user`="{athlete.name}"')
    if result.rowcount == 0:
        # add in user
        ins = table.insert().values(
            user=athlete.name,
            private=athlete.private,
            compulsory=" ".join(athlete.compulsory) if isinstance(athlete.compulsory, list) else athlete.compulsory,
            optional=" ".join(athlete.optional) if isinstance(athlete.optional, list) else athlete.optional,
            password=athlete.password,
            expand_comments=athlete.expand_comments,
            is_coach=athlete.is_coach,
            athletes=json.dumps(athlete.athletes),
            coach_requests=json.dumps(athlete.coach_requests),
            first_login=athlete.first_login,
            signup_date=athlete.signup_date.strftime('%Y-%m-%d') if athlete.signup_date else None,
            messages=json.dumps(athlete.messages),
            dm_prelims1=' '.join(athlete.dm_prelim1) if isinstance(athlete.dm_prelim1, list) else athlete.dm_prelim1,
            dm_prelims2=' '.join(athlete.dm_prelim2) if isinstance(athlete.dm_prelim2, list) else athlete.dm_prelim2,
            dm_finals1=' '.join(athlete.dm_finals1) if isinstance(athlete.dm_finals1, list) else athlete.dm_finals1,
            dm_finals2=' '.join(athlete.dm_finals2) if isinstance(athlete.dm_finals2, list) else athlete.dm_finals2,
            levels=json.dumps(athlete.levels),
            details=json.dumps(athlete.details)
        )
        engine.execute(ins)
    else:
        # else update user
        update = table.update().where(table.c.user==athlete.name).values(
            private=athlete.private,
            compulsory=" ".join(athlete.compulsory) if isinstance(athlete.compulsory, list) else athlete.compulsory,
            optional=" ".join(athlete.optional) if isinstance(athlete.optional, list) else athlete.optional,
            password=athlete.password,
            expand_comments=athlete.expand_comments,
            is_coach=athlete.is_coach,
            athletes=json.dumps(athlete.athletes),
            coach_requests=json.dumps(athlete.coach_requests),
            first_login=athlete.first_login,
            signup_date=athlete.signup_date.strftime('%Y-%m-%d') if athlete.signup_date else None,
            messages=json.dumps(athlete.messages),
            dm_prelims1=' '.join(athlete.dm_prelim1) if isinstance(athlete.dm_prelim1, list) else athlete.dm_prelim1,
            dm_prelims2=' '.join(athlete.dm_prelim2) if isinstance(athlete.dm_prelim2, list) else athlete.dm_prelim2,
            dm_finals1=' '.join(athlete.dm_finals1) if isinstance(athlete.dm_finals1, list) else athlete.dm_finals1,
            dm_finals2=' '.join(athlete.dm_finals2) if isinstance(athlete.dm_finals2, list) else athlete.dm_finals2,
            levels=json.dumps(athlete.levels),
            details=json.dumps(athlete.details)
        )
        engine.execute(update)
    
    result.close()
    conn.close()
    engine.dispose()


def get_users_and_turns(only_users=False):
    """
    Returns all user and turn data from the db
    """
    print(f"~~table name: {TABLE_NAME}")
    engine = create_engine()
    all_turns = []
    if not only_users:
        result = engine.execute(f"SELECT * from `{TABLE_NAME}`")
        all_turns = [res for res in result]
        result.close()
    user_result = engine.execute("SELECT * from `users`")
    conn = engine.connect()
    if os.environ.get("MOCK_DATA", "") == "test":
        y = [x for x in user_result]
        print(len(y), y)
        print({user[0]: user for user in user_result})
    user_data = {
        user[0].lower(): {"private": user[1], "is_coach": user[6], "athletes": json.loads(user[7]), 'details': json.loads(user[17])}
        for user in user_result
    }
    user_result.close()
    conn.close()
    engine.dispose()
    return user_data, all_turns


def get_db_table_data(table):
    """
    Returns all the data from the given table
    """
    engine = create_engine()
    result = engine.execute(f"SELECT * from `{table}`")
    return [r for r in result]


def get_all_simmed_battles():
    """
    Returns all simmed battles
    """
    engine = create_engine()
    result = engine.execute('SELECT * from `battles`')
    if result.rowcount == 0:
        return []
    results = [r for r in result]
    return {
        simmed_battle[0]: {
            'battle_text': json.loads(simmed_battle[1]),
            'winner': simmed_battle[2],
            'leftover_health': simmed_battle[3]
        } for simmed_battle in results
    }


def get_simmed_battle(pokemon1, pokemon2):
    """
    Checks if there was a simulated battle saved in the db
    """
    engine = create_engine()
    pokemon_key = "_".join(sorted([pokemon1, pokemon2]))
    result = engine.execute(f'SELECT * from `battles` WHERE `pokemon_key`="{pokemon_key}"')
    if result.rowcount == 0:
        return {}
    
    # results will have (pokemon_key, battle_text, winner, leftover_health)
    simmed_battle = [row for row in result][0]
    result.close()
    engine.dispose()

    return {
        'battle_text': json.loads(simmed_battle[1]),
        'winner': simmed_battle[2],
        'leftover_health': simmed_battle[3]
    }


def add_simmed_battle(pokemon1, pokemon2, battle_text, winner, leftover_health, update=False):
    """
    Adds in the simmed battle to the database
    """
    engine = create_engine()
    conn = engine.connect()
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("battles", metadata, autoload=True, autoload_with=engine)
    pokemon_key = "_".join(sorted([pokemon1, pokemon2]))
    if update:
        update = table.update().where(table.c.pokemon_key==pokemon_key).values(
            pokemon_key=pokemon_key,
            battle_text=json.dumps(battle_text),
            winner=winner,
            leftover_health=leftover_health
        )
        engine.execute(update)
    else:
        ins = table.insert().values(
            pokemon_key=pokemon_key,
            battle_text=json.dumps(battle_text),
            winner=winner,
            leftover_health=leftover_health
        )
        engine.execute(ins)
    conn.close()
    engine.dispose()

def add_lesson_to_db(title, description, date, coach, plans, new=True):
    """
    Add lesson plan to db for coach
    """
    engine = create_engine()
    metadata = sqlalchemy.MetaData()
    try:
        table = sqlalchemy.Table("lessons", metadata, autoload=True, autoload_with=engine)
    except:
        table = MockTable()
    if new:
        ins = table.insert().values(
            title=title,
            description=description,
            date=date,
            coach=coach,
            plans=plans,
            athletes_completed=json.dumps("{}")
        )
    else:
        ins = table.update().where(table.c.title==title).where(table.c.date==date).where(table.c.coach==coach).values(
            plans=plans,
            description=description
        )
    engine.execute(ins)


def update_lesson(title, date, finished_turns):
    """
    Update the lesson for the athlete
    """
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("lessons", metadata, autoload=True, autoload_with=ENGINE)
    update = table.update().where(table.c.title==title).where(table.c.date==date).values(
        athletes_completed=json.dumps(finished_turns)
    )
    ENGINE.execute(update)


def get_lessons_from_db(coach):
    """
    Returns all lessons from db
    """
    engine = create_engine()
    if coach:
        result = engine.execute(f'SELECT * from `lessons` WHERE LOWER(`coach`)="{coach.lower()}"')
    else:
        result = engine.execute(f'SELECT * from `lessons`;')
    lessons = []
    for lesson in result:
        lessons.append({
            "title": lesson[0],
            "description": lesson[1],
            "date": lesson[2],
            "coach": lesson[3],
            "plans": json.loads(lesson[4]),
            "athletes_completed": json.loads(lesson[5])
        })
    return sorted(lessons, key=lambda lesson: lesson['date'])


def delete_lesson_from_db(coach, title, date):
    """
    Deletes the lesson from the db
    """
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("lessons", metadata, autoload=True, autoload_with=ENGINE)
    delete = table.delete().where(table.c.coach==coach).where(table.c.date==date).where(table.c.title==title)
    return ENGINE.execute(delete)