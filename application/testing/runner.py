'''
 $ python -m application.testing.runner
'''

import os
import sys
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from application.testing.tests import *


class Test:
    def __init__(self, name, func):
        self.name = name
        self.func = func


class Result:
    def __init__(self, name, result):
        self.name = name
        self.result = result
    
    def get_result(self):
        return "PASS" if self.result else "FAIL"


def run_tests(driver, tests):
    """Run all tests"""
    results = []
    for test in tests:
        print(f"Running test: {test.name}")
        try:
            result = test.func(driver)
        except Exception as exc:
            #traceback.print_stack()
            exc_type, exc_value, exc_traceback = sys.exc_info()
            #traceback.print_exception(exc_value, limit=2, file=sys.stdout)
            #traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stdout)
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stdout)
            #print(f"Error: {exc}")
            result = False
        print(f"Test result: {result}")
        results.append(Result(test.name, result))
    return results


if __name__ == '__main__':
    os.environ['FLASK_ENV'] = 'test'
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(executable_path="drivers/chromedriver.exe", chrome_options=chrome_options)

    # browser should be loaded in maximized window
    driver.maximize_window()

    # driver should wait implicitly for a given duration, for the element under consideration to load.
    # to enforce this setting we will use builtin implicitly_wait() function of our 'driver' object.
    driver.implicitly_wait(10) #10 is in seconds
    tests = [
        Test("Test Sign Up", test_signup),
        Test("Test Logging In", test_login),
        Test("Test Entering Data", test_enter_data),
        Test("Test Update Settings", test_update_settings),
        Test("Test Leaderboard Has User", test_leaderboard),
        Test("Test deleting data", test_delete_day)
    ]
    try:
        results = run_tests(driver, tests)
        #assert result is True
    finally:
        delete_test_user()
    
    #driver.close()

    print("\nRESULTS:\n----------------") 
    for result in results:
        print(f"{result.name}: {result.get_result()}")