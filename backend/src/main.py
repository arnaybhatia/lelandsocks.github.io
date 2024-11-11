import json
import os
import time
from datetime import datetime
import pickle
import concurrent.futures

import pytz
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from make_webpage import make_index_page, make_user_page

load_dotenv()


# --- functions ---  # PEP8: `lower_case_names`
def save_cookies(driver, path):
    with open(path, 'wb') as file:
        pickle.dump(driver.get_cookies(), file)

def load_cookies(driver, path):
    try:
        with open(path, 'rb') as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        return True
    except:
        return False

def login():
    INVESTOPEDIA_EMAIL = os.environ.get("INVESTOPEDIA_EMAIL")
    INVESTOPEDIA_PASSWORD = os.environ.get("INVESTOPEDIA_PASSWORD")
    COOKIE_PATH = "./backend/cookies.pkl"

    # First try to use cookies
    driver.get("https://www.investopedia.com")
    if load_cookies(driver, COOKIE_PATH):
        driver.get(r"https://www.investopedia.com/simulator/home.aspx")
        time.sleep(5)
        # Check if we're actually logged in by looking for a login button
        if not driver.find_elements(By.ID, "login"):
            return

    # If cookies didn't work, do regular login
    driver.get(r"https://www.investopedia.com/simulator/home.aspx")
    time.sleep(10)

    driver.find_element(By.ID, "username").send_keys(INVESTOPEDIA_EMAIL)
    time.sleep(0.5)

    driver.find_element(By.ID, "password").send_keys(INVESTOPEDIA_PASSWORD)
    time.sleep(0.5)

    driver.find_element(By.ID, "login").click()
    time.sleep(5)
    
    # Save cookies after successful login
    save_cookies(driver, COOKIE_PATH)


def process_single_account(url):
    """Process a single account and return its information"""
    try:
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
        
        login()
        
        driver.get(url)
        time.sleep(10)
        
        account_value = driver.find_element(
            By.XPATH, '//*[@data-cy="account-value-text"]'
        ).text
        account_value = float(account_value.replace("$", "").replace(",", ""))
        account_name = driver.find_element(
            By.XPATH, '//*[@data-cy="user-portfolio-name"]'
        ).text.replace(" Portfolio", "")

        table = driver.find_element(By.XPATH, "//table")
        rows = table.find_elements(By.TAG_NAME, "tr")
        stock_data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            cols = [col.text for col in cols]
            stock_data.append(cols)
            
        if stock_data == ["user has no stock holdings yet"]:
            stock_data = []
        stock_data = [[s for s in sub_list if s] for sub_list in stock_data]
        
        driver.quit()
        return account_name, [account_value, url.strip(), stock_data]
    except Exception as e:
        print(f"Error processing account {url}: {str(e)}")
        return None

def get_account_information():
    """Returns a dictionary with all of the account values within it"""
    account_information = {}
    urls = []
    
    with open("./backend/portfolios/portfolios.txt", "r") as file:
        urls = [line.strip() for line in file]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(process_single_account, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            result = future.result()
            if result:
                account_name, account_data = result
                account_information[account_name] = account_data
    
    return account_information


# Write to a time-stamped file for storage reasons, NY timezone because finance moment
# in_time represents the leaderboards that are in time, out_of_time represents the ones that are out of time
# This is because I don't want the leaderboard to just have a bunch of straight lines when it is waiting for the next day to happen
tz_NY = pytz.timezone("America/New_York")
curr_time = datetime.now(tz_NY)

# Check if the current day is a weekday
if curr_time.weekday() < 5:  # 0 = Monday, 4 = Friday
    if (
        (curr_time.hour > 9 or (curr_time.hour == 9 and curr_time.minute >= 30))
        and curr_time.hour < 17
    ) or os.environ.get("FORCE_UPDATE") == "True":
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

# Now make the user leaderboards into html files, this should always run just to give the impression that the leaderboard actually updates lol
with open("index.html", "w") as file:
    file.write(make_index_page())
with open("./backend/portfolios/usernames.txt", "r") as file:
    usernames = file.readlines()
    usernames = [user.strip() for user in usernames]
for user in usernames:
    with open(f"./players/{user}.html", "w") as file:
        file.write(make_user_page(user))