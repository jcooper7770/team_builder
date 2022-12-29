'''
'''

import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sqlalchemy

from application.utils.database import create_engine


def create_new_user(driver, username, password1, password2):
    """ Creats new user"""
    sign_up = driver.find_element(By.XPATH,'//h2[text()="Sign-Up"]')

    actions = ActionChains(driver)
    actions.move_to_element(sign_up).perform()

    driver.find_element(By.ID,"username").send_keys(username)
    driver.find_element(By.ID,"password").send_keys(password1)
    driver.find_element(By.ID,"confirm").send_keys(password2)
    driver.find_element(By.ID,"yes").click()
    driver.find_element(By.XPATH,'//button').click()


def input_and_validate_skills(driver, skills):
    """Input data and verify it shows"""
    driver.find_element(By.ID,"log").send_keys(" ".join(skills))
    driver.find_element(By.XPATH,'//button[text()="Submit"]').click()
    wait_for_load(driver)
    driver.find_element(By.ID,"minimize_practices").click()
    driver.find_element(By.XPATH,'//th[contains(text(),"(trampoline)")]').click()
    skills.extend('')
    table_xpath = make_xpath_by_table_cols(skills)
    wait_for_element(driver, table_xpath)


def wait_for_element(driver, xpath, wait_time=10):
    """Wait for an element by xpath"""
    # Wait for initialize, in seconds
    return WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.XPATH, xpath)))


def click_popup(driver):
    """click pop up"""
    alert = driver.switch_to.alert
    print(f"alert message: {alert.text}")
    alert.accept()
    #driver.switch_to.window('main')


def wait_for_load(driver, wait_time=10):
    """Wait for page load"""
    print("waiting for load")
    for _ in range(wait_time):
        x = driver.execute_script("return document.readyState")
        if x == "complete":
            break
        time.sleep(1)
    print("Done loading")


def make_xpath_by_table_cols(cols):
    """make xpath"""
    xpath = f'//*[text()="{cols[0]}"]'
    if len(cols) == 1:
        return xpath
    # //*[text()="40o"]/following-sibling::td[text()="40<"]/following-sibling::td[text()="40/"]/following-sibling::td[text()="40o"]
    for col in cols[1:]:
        if col == '':
            xpath = f'{xpath}/following-sibling::td[not(text())]'
        else:
            xpath = f'{xpath}/following-sibling::td[text()="{col}"]'
    return xpath


def login(driver):
    """login"""
    login = driver.find_element(By.XPATH,'//h2[text()="Login"]')

    actions = ActionChains(driver)
    actions.move_to_element(login).perform()

    driver.find_element(By.ID,"username").send_keys("test_user")
    driver.find_element(By.ID,"password").send_keys("password")
    driver.find_element(By.XPATH,'//button[text()="Login"]').click()



def logout(driver):
    """Logout"""
    driver.find_element(By.XPATH,'//a[contains(text(),"Hello test_user")]').click()
    driver.find_element(By.XPATH,'//a[text()="Logout"]').click()
    driver.find_element(By.XPATH,'//h2[text()="Login"]')


def delete_test_user():
    """Deletes test user from db"""
    print("~~ Cleaning up data ~~")
    engine = create_engine()
    metadata = sqlalchemy.MetaData()
    table = sqlalchemy.Table("users", metadata, autoload=True, autoload_with=engine)
    delete = table.delete().where(table.c.user=="test_user")
    deleted = engine.execute(delete)
    print(f"deleted {deleted.rowcount} users")

    table = sqlalchemy.Table("test_db", metadata, autoload=True, autoload_with=engine)
    delete = table.delete().where(table.c.user=="test_user")
    deleted = engine.execute(delete)
    print(f"deleted {deleted.rowcount} rows from data")