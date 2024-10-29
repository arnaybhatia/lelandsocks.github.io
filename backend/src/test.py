from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager
import os
from dotenv import load_dotenv

load_dotenv()

# --- functions ---  # PEP8: `lower_case_names`
def login():
    INVESTOPEDIA_EMAIL = os.environ.get("INVESTOPEDIA_EMAIL")
    INVESTOPEDIA_PASSWORD = os.environ.get("INVESTOPEDIA_PASSWORD")
    
    driver.get(r'https://www.investopedia.com/simulator/home.aspx')
    driver.implicitly_wait(10)
    
    driver.find_element(By.ID, 'username').send_keys(INVESTOPEDIA_EMAIL)
    driver.find_element(By.ID, 'password').send_keys(INVESTOPEDIA_PASSWORD)
    driver.find_element(By.ID, 'login').click()

def get_stock_table(url):
    driver.get(url)
    table = driver.find_element(By.XPATH, '//table')
    rows = table.find_elements(By.TAG_NAME, 'tr')
    
    stock_data = []
    for row in rows:
        cols = row.find_elements(By.TAG_NAME, 'td')
        cols = [col.text for col in cols]
        stock_data.append(cols)
    
    return stock_data

# --- main ---
driver = webdriver.Firefox()
login()
url = 'https://www.investopedia.com/simulator/games/user-portfolio?portfolio=10445735'
stock_table = get_stock_table(url)
for row in stock_table:
    print(row)
driver.close()
