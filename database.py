"""
Database operations
"""


from ast import Return
import sqlalchemy

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


def create_engine(table_name=None):
    table_name = table_name or TABLE_NAME
    global ENGINE
    global DB_TABLE
    url = "itsflippincoop.com" if table_name == "test_data" else "127.0.0.1"
    db_name = "tramp" if os.environ.get("FLASK_ENV", "prod") == "prod" else "test_tramp"
    print(f"Using db: {db_name}")
    engine = sqlalchemy.create_engine(f'mysql+pymysql://itsflippincoop:password@itsflippincoop.com:3306/{db_name}', echo=True)
    ENGINE = engine
    metadata = sqlalchemy.MetaData()
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
        "password": user[4]
    }


def add_to_db(turns, user, event, practice_date, table=None):
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
                date=practice_date
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
                note=turn['note']
            )
            engine.execute(ins)


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


def get_from_db(table_name=None, user="test", date=None):
    table_name = table_name or TABLE_NAME
    engine = create_engine(table_name)

    if date:
        result = engine.execute(f'SELECT * from `{table_name}` WHERE (LOWER({table_name}.user)="{user.lower()}" AND {table_name}.date="{date}");')
    else:
        result = engine.execute(f'SELECT * from `{table_name}` WHERE LOWER({table_name}.user)="{user.lower()}";')
    
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
    # First check if user exists
    result = engine.execute(f'SELECT * from `users` WHERE `user`="{athlete.name}"')
    if result.rowcount == 0:
        # add in user
        ins = table.insert().values(
            user=athlete.name,
            private=athlete.private,
            compulsory=" ".join(athlete.compulsory) if isinstance(athlete.compulsory, list) else athlete.compulsory,
            optional=" ".join(athlete.optional) if isinstance(athlete.optional, list) else athlete.optional,
            password=athlete.password
        )
        engine.execute(ins)
    else:
        # else update user
        update = table.update().where(table.c.user==athlete.name).values(
            private=athlete.private,
            compulsory=" ".join(athlete.compulsory) if isinstance(athlete.compulsory, list) else athlete.compulsory,
            optional=" ".join(athlete.optional) if isinstance(athlete.optional, list) else athlete.optional,
            password=athlete.password
        )
        engine.execute(update)
    
    result.close()
    conn.close()
    engine.dispose()


def get_users_and_turns():
    """
    Returns all user and turn data from the db
    """
    engine = create_engine()
    result = engine.execute(f"SELECT * from `{TABLE_NAME}`")
    user_result = engine.execute("SELECT * from `users`")
    conn = engine.connect()
    all_turns = [res for res in result]
    user_data = {
        user[0].lower(): {"private": user[1]}
        for user in user_result
    }
    result.close()
    user_result.close()
    conn.close()
    engine.dispose()
    return user_data, all_turns


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


def add_simmed_battle(pokemon1, pokemon2, battle_text, winner, leftover_health):
    """
    Adds in the simmed battle to the database
    """
    engine = create_engine()
    conn = engine.connect()
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("battles", metadata, autoload=True, autoload_with=engine)
    ins = table.insert().values(
        pokemon_key="_".join(sorted([pokemon1, pokemon2])),
        battle_text=json.dumps(battle_text),
        winner=winner,
        leftover_health=leftover_health
    )
    engine.execute(ins)
    conn.close()
    engine.dispose()