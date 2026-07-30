import datetime

MOCK_USER = [
    "name", False, "", "", "", True,
    #False, # is_coach
    False, # is_coach
    '["bob"]', False, "2024-01-21", "[]",
    "", "", "", "", # dm passes,
    "[1, 1, 2]", "[]", '{"first_name": "firstName", "last_name": "lastName"}'
]
MOCK_USER2 = [
    "bob", False, "", "", "", True,
    #False, # is_coach
    False, # is_coach
    '["bob"]', False, "2024-01-21", "[]",
    "", "", "", "", # dm passes,
    "[1, 1, 2]", "[]", '{"first_name": "bob", "last_name": "lastName"}'
]
MOCK_DATA = [
    1, "12001<", datetime.datetime.now(), "bob", "trampoline", "note", 'tag1,tag2'
]
MOCK_LESSON = [
    "title", "description", "2024-01-22", 'coach', '["plan1", "plan2"]'
]

class MockResult:
    def __init__(self, values, rowcount=1):
        self.values = values
        self.rowcount = rowcount

    def close(self):
        return
    
    def __iter__(self):
        return iter(self.values)

class MockEngine2:
    """
    Mock database engine if not connected to internet
    """
    def __init__(self):
        """
        """
        pass

    def execute(self, string):
        """
        execute the query
        """
        if not string:
            return MockResult([])
        if "from `users`" in string:
            return MockResult([
                [*MOCK_USER],
                [*MOCK_USER2]
            ])
        elif "from `test_db`" in string:
            return MockResult([
                [*MOCK_DATA]
            ])
        elif 'from `ratings`' in string:
            return MockResult([])
        elif 'from `airtimes`' in string:
            return MockResult([])
        elif 'from `lessons' in string:
            return MockResult([
                [*MOCK_LESSON]
            ])
        elif 'from `goals' in string:
            return MockResult([])

    def connect(self):
        return MockConnection()

    def dispose(self):
        return

class MockConnection():
    def close(self):
        return

class MockWhere:
    def values(self, *args, **kwargs):
        return
    
    def where(self, *args, **kwargs):
        return MockWhere()

class MockUpdate:
    def where(self, *args, **kwargs):
        return MockWhere()

class MockC:
    user = "user"

class MockTable2:
    """
    Mock the table
    """
    
    def __init__(self):
        self.c = MockC()

    def update(self):
        return MockWhere()