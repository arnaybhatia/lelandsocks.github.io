from selenium import webdriver
from selenium.webdriver.common.by import By
#from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import time
import os
from dotenv import load_dotenv

load_dotenv()

# --- functions ---  # PEP8: `lower_case_names`

def login():
    INVESTOPEDIA_EMAIL=os.environ.get("INVESTOPEDIA_EMAIL")
    INVESTOPEDIA_PASSWORD=os.environ.get("INVESTOPEDIA_PASSWORD")
    
    driver.get(r'https://www.investopedia.com/simulator/home.aspx')
    driver.implicitly_wait(10)
        
    driver.find_element(By.ID, 'username').send_keys(INVESTOPEDIA_EMAIL)
    time.sleep(0.5)
    
    driver.find_element(By.ID, 'password').send_keys(INVESTOPEDIA_PASSWORD)
    time.sleep(0.5)
    
    driver.find_element(By.ID, 'login').click()
    time.sleep(0.5)

def get_leaderboard_page():
    url = r'https://www.investopedia.com/simulator/games'
    driver.get(url)

def set_stock(ticker):
    driver.find_element(By.XPATH, '//input[@placeholder="Look up Symbol/Company Name"]').send_keys(ticker)
    
    #driver.find_element(By.XPATH, '//div[@role="option"]').click()
    
    option = driver.find_element(By.XPATH, '//div[@role="option"]')
    driver.execute_script('arguments[0].click()', option)

# --- main ---

driver = webdriver.Firefox()
#driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())

login()
get_leaderboard_page()
#set_stock('hvt')

#driver.close()
