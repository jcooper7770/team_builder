'''
 $ python -m application.testing.test
'''

import datetime
import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlalchemy

from application.utils.database import create_engine
from application.testing.utils import *


def test_signup(driver):
    """Test signup page"""
    base_url = "http://127.0.0.1:5000/login"
    # declare and initialize driver variable

    # to load a given URL in browser window
    driver.get(base_url)

    print(driver.title)
    # test whether correct URL/ Web Site has been loaded or not
    assert "Trampoline Logger" in driver.title

    ## Test for creating a user
    driver.find_element(By.ID,"sign-up").click()

    create_new_user(driver, "test_user", "password", "password2")
   
    try:
        error_element = driver.find_element(By.XPATH,'//b[text()="Passwords do not match"]')
        print(error_element.text)
    except:
        print("Failed to find the error text after unmatched passwords")
        return False
    
    create_new_user(driver, "test_user", "password", "password")
    return True


def test_login(driver):
    """Test login"""
    # Login     
    login(driver)

    # Verify it went to the about page on first login
    driver.find_element(By.XPATH,'//h2[text()="Recording turns"]')

    # Go to the home page
    driver.find_element(By.XPATH,'//a[text()="Home"]').click()

    # Verify second login goes to home page
    logout(driver)
    login(driver)
    return True


def test_enter_data(driver):
    """Test entering data"""
    # test entering data
    driver.find_element(By.ID,"minimize_practices").click()
    driver.find_element(By.ID,"log").send_keys("40o<//<o")
    driver.find_element(By.XPATH,'//button[text()="Submit"]').click()
    wait_for_load(driver)

    # Verify data was entered
    driver.find_element(By.ID,"minimize_practices").click()
    driver.find_element(By.XPATH,'//th[contains(text(),"(trampoline)")]').click()
    table_xpath = make_xpath_by_table_cols(['40o', '40<', '40/', '40/', '40<', '40o', '', '6', '6', '6.0', '6.0', '3.4', '3.4'])
    wait_for_element(driver, table_xpath)

    
    # Test recommendations
    driver.find_element(By.ID,"log").send_keys("40o")
    driver.find_element(By.XPATH,'//a[@id="skill40<"][text()="40<"]').click()
    driver.find_element(By.XPATH,'//a[@id="skill40/"][text()="40/"]').click()
    driver.find_element(By.XPATH,'//button[text()="Submit"]').click()
    wait_for_load(driver)
    driver.find_element(By.ID,"minimize_practices").click()
    driver.find_element(By.XPATH,'//th[contains(text(),"(trampoline)")]').click()
    table_xpath = make_xpath_by_table_cols(['40o', '40<', '40/', '', '3', '9', '3.0', '9.0', '1.7', '5.1'])
    wait_for_element(driver, table_xpath)

    # Enter a whole routine
    input_and_validate_skills(driver, ['12001<', '811<', '12001o', '813<', '803<', '813o', '803o', '800<' ,'801<', '822/'])
    '''
    driver.find_element(By.ID,"log").send_keys("12001< 811< 12001o 813< 803< 813o 803o 800< 801< 822/")
    driver.find_element(By.XPATH,'//button[text()="Submit"]').click()
    wait_for_load(driver)
    driver.find_element(By.ID,"minimize_practices").click()
    driver.find_element(By.XPATH,'//th[contains(text(),"(trampoline)")]').click()
    table_xpath = make_xpath_by_table_cols(['12001<', '811<', '12001o', '813<', '803<', '813o', '803o', '800<', '801<', '822/', '', '10', '19', '22.0', '31.0', '15.0', '21.1'])
    wait_for_element(driver, table_xpath)
    '''

    # Enter on a diff day (DMT)
    driver.find_element(By.ID, "logger-date").send_keys("04/22/2022")
    driver.find_element(By.ID, "event").click()
    driver.find_element(By.XPATH, '//option[text()="Double Mini"]').click()
    input_and_validate_skills(driver, ['12001o', '12101o'])


    # Remove the day
    #driver.find_element(By.XPATH,'//a[@title="remove day"]//child::span').click()
    #click_popup(driver)
    #wait_for_load(driver)
    return True


def test_delete_day(driver):
    """Delete a day of data"""
    driver.find_element(By.XPATH,'//a[text()="Home"]').click()
    wait_for_load(driver)

    driver.find_element(By.ID,"minimize_practices").click()
    xpath = '//th[text()="Friday 04/22/2022 (dmt)"]/child::button[@id="delete-button"]/child::a[@title="remove day"]//child::span'
    driver.find_element(By.XPATH, xpath).click()
    click_popup(driver)
    wait_for_load(driver, wait_time=30)

    # Check leaderboard for day removed?
    return True


def test_update_settings(driver):
    """Test updating user settings"""
    # Open user settings
    driver.find_element(By.XPATH,'//a[contains(text(),"Hello test_user")]').click()
    driver.find_element(By.XPATH,'//a[text()="User Profile"]').click()

    #Wait for user settings to open
    wait_for_element(driver, "//h2[text()='User Settings for test_user']")

    # Change from private to public
    driver.find_element(By.XPATH, '//label[text()="No, show data in leaderboards"]/preceding-sibling::input[@id="no"]').click()
    driver.find_element(By.XPATH, '//button[text()="Save"]').click()
    wait_for_load(driver)
    return True


def test_leaderboard(driver):
    """Test the leaderboard has the user"""
    # click landing page link
    driver.find_element(By.XPATH, '//img[@alt="Logo"]').click()
    wait_for_element(driver, '//h2[text()="Trampoline Practice Logger"]')

    today = datetime.date.today()
    date_str = today.strftime("%m/%d/%Y")
    # Validate trampoline routine
    table_xpath = make_xpath_by_table_cols(['test_user', f'15.0 ({date_str})'])
    wait_for_element(driver, table_xpath)

    # Validate dmt pass
    table_xpath = make_xpath_by_table_cols(['test_user', f'10.8 (04/22/2022)'])
    wait_for_element(driver, table_xpath)

    # Validate trampoline turns
    table_xpath = make_xpath_by_table_cols(['test_user', '3'])
    wait_for_element(driver, table_xpath)

    # Validate dmt flips
    table_xpath = make_xpath_by_table_cols(['test_user', '6.0'])
    wait_for_element(driver, table_xpath)

    # Validate trampoline flips
    table_xpath = make_xpath_by_table_cols(['test_user', '31.0'])
    wait_for_element(driver, table_xpath)

    # Take a screenshot 
    element = driver.find_element(By.XPATH, table_xpath)
    actions = ActionChains(driver)
    actions.move_to_element(element).perform()
    driver.save_screenshot('leaderboard.png')

    return True