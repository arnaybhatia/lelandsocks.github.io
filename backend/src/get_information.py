import json
import os
import time
from datetime import datetime

import pytz
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from make_webpage import make_index_page, make_user_page

load_dotenv()


# --- functions ---  # PEP8: `lower_case_names`
def login():
    INVESTOPEDIA_EMAIL = os.environ.get("INVESTOPEDIA_EMAIL")
    INVESTOPEDIA_PASSWORD = os.environ.get("INVESTOPEDIA_PASSWORD")

    driver.get(r"https://www.investopedia.com/simulator/home.aspx")
    driver.implicitly_wait(10)

    driver.find_element(By.ID, "username").send_keys(INVESTOPEDIA_EMAIL)
    time.sleep(0.5)

    driver.find_element(By.ID, "password").send_keys(INVESTOPEDIA_PASSWORD)
    time.sleep(0.5)

    driver.find_element(By.ID, "login").click()
    time.sleep(0.5)
    # print("done with login!!!")


def get_account_information():
    """Returns a list with all of the account values within it"""
    account_information = {}
    with open("./backend/portfolios/portfolios.txt", "r") as file:
        for line in file:
            driver.get(
                rf"{line}"
            )  # what the heck is a french string doing here: https://stackoverflow.com/a/58321139
            time.sleep(5)
            print(driver.current_url)
            # driver.save_screenshot("screenie.png")
            account_value = driver.find_element(
                By.XPATH, '//*[@data-cy="account-value-text"]'
            ).text
            account_value = float(account_value.replace("$", "").replace(",", ""))
            account_name = driver.find_element(
                By.XPATH, '//*[@data-cy="user-portfolio-name"]'
            ).text.replace(" Portfolio", "")  # just getting the account name

            # Extract stock data
            table = driver.find_element(By.XPATH, "//table")
            rows = table.find_elements(By.TAG_NAME, "tr")
            stock_data = []
            print(driver.current_url)
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                cols = [col.text for col in cols]
                stock_data.append(cols)
            if stock_data == [
                "user has no stock holdings yet"
            ]:  # Ensure that if the user has no stocks, the list is empty
                stock_data = []
            print(stock_data)
            account_information[account_name] = [
                account_value,
                line.strip(),
                stock_data,
            ]
            print(line.strip(), account_value, account_name)
    return account_information


# Write to a time-stamped file for storage reasons, NY timezone because finance moment
# in_time represents the leaderboards that are in time, out_of_time represents the ones that are out of time
# This is because I don't want the leaderboard to just have a bunch of straight lines when it is waiting for the next day to happen
tz_NY = pytz.timezone("America/New_York")
curr_time = datetime.now(tz_NY)

# Check if the current day is a weekday
if curr_time.weekday() < 5:  # 0 = Monday, 4 = Friday
    if (
        curr_time.hour > 9 or (curr_time.hour == 9 and curr_time.minute >= 30)
    ) and curr_time.hour < 16:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-crash-reporter")
        options.add_argument("--disable-oopr-debug-crash-dump")
        options.add_argument("--no-crash-upload")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-low-res-tiling")
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        options.add_argument("--incognito")
        options.add_argument("--disable-cache")
        driver = webdriver.Chrome(options=options)
        driver.delete_all_cookies()

        # login to the website
        login()

        # Perform the tasks
        account_values = get_account_information()  # List of the values of the users
        file_name = f"./backend/leaderboards/in_time/leaderboard-{curr_time.strftime('%Y-%m-%d-%H_%M')}.json"
        with open(file_name, "w") as file:
            json.dump(account_values, file)
        # Write to a latest file to make it easy to read into a cool file at the end
        with open(
            "./backend/leaderboards/leaderboard-latest.json", "w"
        ) as file:  # latest is the file that is read by the webpage, saved in main directory for fun
            json.dump(account_values, file)

        driver.close()
        with open("index.html", "w") as file:
            file.write(make_index_page())

        # Now make the user leaderboards

        for user in account_values:
            with open(f"./players/{user}.html", "w") as file:
                file.write(make_user_page(user))
