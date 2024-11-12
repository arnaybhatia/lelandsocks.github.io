import json
import os
import time
from datetime import datetime
import pickle
import concurrent.futures
import random
import asyncio
from playwright.async_api import async_playwright

import pytz
from dotenv import load_dotenv
from make_webpage import make_index_page, make_user_page

load_dotenv()

# Add list of user agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

# --- functions ---  # PEP8: `lower_case_names`
async def save_cookies(context, path):
    cookies = await context.cookies()
    with open(path, 'wb') as file:
        pickle.dump(cookies, file)

async def load_cookies(context, path):
    try:
        with open(path, 'rb') as file:
            cookies = pickle.load(file)
            await context.add_cookies(cookies)
        return True
    except:
        return False

async def login(page):
    INVESTOPEDIA_EMAIL = os.environ.get("INVESTOPEDIA_EMAIL")
    INVESTOPEDIA_PASSWORD = os.environ.get("INVESTOPEDIA_PASSWORD")
    COOKIE_PATH = "./backend/cookies.pkl"

    # First try to use cookies
    await page.goto("https://www.investopedia.com")
    if await load_cookies(page.context, COOKIE_PATH):
        await page.goto("https://www.investopedia.com/simulator/home.aspx")
        await page.wait_for_timeout(5000)
        # Check if we're logged in
        login_button = await page.query_selector("#login")
        if not login_button:
            return

    # If cookies didn't work, do regular login
    await page.goto("https://www.investopedia.com/simulator/home.aspx")
    await page.wait_for_timeout(5000)

    await page.fill("#username", INVESTOPEDIA_EMAIL)
    await page.fill("#password", INVESTOPEDIA_PASSWORD)
    await page.click("#login")
    await page.wait_for_timeout(5000)
    
    # Save cookies after successful login
    await save_cookies(page.context, COOKIE_PATH)

# Add after imports
SCREENSHOT_DIR = "./backend/error_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def process_single_account(url):
    """Process a single account and return its information"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
        )
        context = await browser.new_context(
            user_agent=get_random_user_agent(),
        )
        page = await context.new_page()
        
        try:
            # First attempt
            await login(page)
            await page.goto(url)
            await page.wait_for_timeout(2000)
            print(page.url)
            
            try:
                account_value = await page.text_content('[data-cy="account-value-text"]')
                account_value = float(account_value.replace("$", "").replace(",", ""))
                account_name = await page.text_content('[data-cy="user-portfolio-name"]')
                account_name = account_name.replace(" Portfolio", "").strip()  # Added strip()
            except Exception as first_error:
                print("First attempt failed, trying again with fresh login...")
                await context.clear_cookies()
                await login(page)
                await page.goto(url)
                await page.wait_for_timeout(100)
                
                account_value = await page.text_content('[data-cy="account-value-text"]')
                account_value = float(account_value.replace("$", "").replace(",", ""))
                account_name = await page.text_content('[data-cy="user-portfolio-name"]')
                account_name = account_name.replace(" Portfolio", "").strip()  # Added strip()

            # Get stock data from table
            stock_data = []
            rows = await page.query_selector_all("table tr")
            
            print(f"\nProcessing account: {account_name}")
            print("Table rows found:", len(rows))
            
            if len(rows) > 1:  # Skip header row
                for i, row in enumerate(rows[1:], 1):
                    try:
                        # # Print entire row content for debugging
                        # all_cells = await row.query_selector_all("td")
                        # raw_row_data = []
                        # for cell in all_cells:
                        #     content = await cell.text_content()
                        #     raw_row_data.append(content.strip())
                        # print(f"Row {i} raw data:", raw_row_data)
                        
                        symbol = await row.query_selector("td:nth-child(1)")
                        last_price = await row.query_selector("td:nth-child(3)")
                        gain_pct = await row.query_selector("td:nth-child(8)")
                        
                        if symbol and last_price and gain_pct:
                            symbol_text = (await symbol.text_content()).strip()
                            price_text = (await last_price.text_content()).strip()
                            gain_text = (await gain_pct.text_content()).strip()
                            # Clean up gain percentage text
                            gain_text = gain_text.replace("\n", "").replace(" ", "")
                            gain_parts = gain_text.split("(")
                            if len(gain_parts) > 1:
                                gain_text = gain_parts[1].replace(")", "").replace("%", "")
                            
                            if symbol_text and price_text and gain_text:
                                stock_data.append([symbol_text, price_text, gain_text])
                                print(f"Processed stock: {symbol_text} ${price_text} {gain_text}%")
                    except Exception as e:
                        print(f"Error parsing row: {e}")
                        continue

            if not stock_data:
                stock_data = []
            
            return account_name.strip(), [account_value, url.strip(), stock_data]  # Added strip()
        except Exception as e:
            print(f"Error processing account {url}: {str(e)}")
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            screenshot_path = os.path.join(SCREENSHOT_DIR, f"error_{timestamp}_{url.split('/')[-1]}.png")
            await page.screenshot(path=screenshot_path)
            return None
        finally:
            await browser.close()

async def get_account_information():
    """Returns a dictionary with all of the account values within it"""
    account_information = {}
    urls = []
    
    with open("./backend/portfolios/portfolios.txt", "r") as file:
        urls = [line.strip() for line in file]
    
    # Create semaphore to limit concurrent executions
    semaphore = asyncio.Semaphore(16)
    
    async def process_with_semaphore(url):
        async with semaphore:
            return await process_single_account(url)
    
    tasks = [process_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    for result in results:
        if result:
            account_name, account_data = result
            account_information[account_name] = account_data
    
    return account_information

def generate_user_page(user):
    """Helper function to generate a single user's page"""
    with open(f"./players/{user}.html", "w") as file:
        file.write(make_user_page(user))

# Main execution block
async def main():
    tz_NY = pytz.timezone("America/New_York")
    curr_time = datetime.now(tz_NY)

    if curr_time.weekday() < 5:
        if ((curr_time.hour > 9 or (curr_time.hour == 9 and curr_time.minute >= 30))
            and curr_time.hour < 17) or os.environ.get("FORCE_UPDATE") == "True":
            
            account_values = await get_account_information()
            
            file_name = f"./backend/leaderboards/out_of_time/leaderboard-{curr_time.strftime('%Y-%m-%d-%H_%M')}.json"
            if ((curr_time.hour > 9 or (curr_time.hour == 9 and curr_time.minute >= 30)) and curr_time.hour < 17):
                file_name = f"./backend/leaderboards/in_time/leaderboard-{curr_time.strftime('%Y-%m-%d-%H_%M')}.json"
            
            with open(file_name, "w") as file:
                json.dump(account_values, file)
            
            with open("./backend/leaderboards/leaderboard-latest.json", "w") as file:
                json.dump(account_values, file)
            
            # Update index.html
            with open("index.html", "w") as file:
                file.write(make_index_page())
            
            # Read usernames
            with open("./backend/portfolios/usernames.txt", "r") as file:
                usernames = [user.strip() for user in file.readlines()]
            
            # Parallelize user page generation
            with concurrent.futures.ProcessPoolExecutor() as executor:
                executor.map(generate_user_page, usernames)

if __name__ == "__main__":
    asyncio.run(main())