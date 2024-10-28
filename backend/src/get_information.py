from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os
import json
from dotenv import load_dotenv
import datetime

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
    print(driver.current_url)
    print("done with login!!!")


def get_leaderboard_page():
    url = r"https://www.investopedia.com/simulator/games"
    driver.get(url)


def set_stock(ticker):
    driver.find_element(
        By.XPATH, '//input[@placeholder="Look up Symbol/Company Name"]'
    ).send_keys(ticker)
    option = driver.find_element(By.XPATH, '//div[@role="option"]')
    driver.execute_script("arguments[0].click()", option)


# def get_user_account_information():
#    INVESTOPEDIA_USER_ID = int(os.environ.get("INVESTOPEDIA_USER_ID"))
#    driver.get(r"https://www.investopedia.com/simulator/portfolio")
#    time.sleep(10)
#    # print(driver.current_url)
#    account_value = driver.find_element(
#        By.XPATH, '//div[contains(text(), "Account Value")]/following-sibling::div'
#    ).text
#    account_value = float(account_value.replace("$", "").replace(",", ""))
#    account_name = driver.find_element(
#        By.XPATH, '//*[@data-cy="account-value-text"]'
#    ).text.replace(" Portfolio", "")  # just getting the account name
#    print(
#        f"https://www.investopedia.com/simulator/games/user-portfolio?portfolio={INVESTOPEDIA_USER_ID}",
#        account_value,
#        account_name,
#    )
#    return (
#        account_name,
#        account_value,
#        f"https://www.investopedia.com/simulator/games/user-portfolio?portfolio={INVESTOPEDIA_USER_ID}",
#    )


def get_account_information():
    """Returns a list with all of the account values within it"""
    account_information = {}
    with open("./backend/portfolios/portfolios.txt", "r") as file:
        for line in file:
            driver.get(
                rf"{line}"
            )  # what the heck is a french string doing here: https://stackoverflow.com/a/58321139
            # print(driver.current_url)
            time.sleep(3)
            # print(driver.current_url)
            account_value = driver.find_element(
                By.XPATH, '//*[@data-cy="account-value-text"]'
            ).text
            account_value = float(account_value.replace("$", "").replace(",", ""))
            account_name = driver.find_element(
                By.XPATH, '//*[@data-cy="user-portfolio-name"]'
            ).text.replace(" Portfolio", "")  # just getting the account name
            account_information[account_name] = [account_value, line.strip()]
            print(line.strip(), account_value, account_name)
    return account_information


# --- main ---
# Clear the cache, set options needed

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
driver = webdriver.Chrome(options=options)
driver.delete_all_cookies()

# Perform the tasks
login()
get_leaderboard_page()
account_values = get_account_information()  # List of the values of the users

# Removed as I just made the portfolios.txt file have my own user!
# a, b, c = (
#    get_user_account_information()
# )  # Get the value of the person who is running this service (me) :)
# account_values |= {a: [b, c]}  # add the information to the dictionary
# print(account_values[a], account_values)
# Now sort the dictionary to make the leaderboard
# account_values = dict(sorted(account_values.items()[0]))

# Write to a time-stamped file for storage reasons
file_name = f"./backend/leaderboards/leaderboard-{datetime.datetime.utcnow().strftime("%Y-%m-%d-%H_%M")}.json"
with open(file_name, "w") as file:
    json.dump(account_values, file)
# Write to a latest file to make it easy to read into a cool file at the end
with open("./backend/leaderboards/leaderboard-latest.json", "w") as file:
    json.dump(account_values, file)
driver.close()
