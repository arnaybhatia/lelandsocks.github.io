import asyncio
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()


async def wait_for(time_to_wait):
    await asyncio.sleep(time_to_wait / 1000)


async def main(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36"
        )
        page = await context.new_page()
        # await stealth_async(page)
        link = "https://investopedia.com/simulator"
        file_written = False

        try:
            await page.set_viewport_size({"width": 1920, "height": 1080})

            async def intercept_response(response):
                if (
                    response.url
                    == "https://www.investopedia.com/auth/realms/investopedia/protocol/openid-connect/token"
                ):
                    response_json = await response.json()
                    with open("./auth.json", "w") as f:
                        json.dump(response_json, f)
                    nonlocal file_written
                    file_written = True

            page.on("response", intercept_response)

            await page.goto(link, wait_until="load", timeout=15000)

            login_button = await page.wait_for_selector(
                '//span[contains(text(),"LOG IN")]', timeout=3000
            )
            await login_button.click()
            await wait_for(6000)

            username_field = await page.wait_for_selector(
                '//input[@id="username"]', timeout=3000
            )
            password_field = await page.wait_for_selector(
                '//input[@id="password"]', timeout=3000
            )
            sign_in_button = await page.wait_for_selector(
                '//input[@id="login"]', timeout=3000
            )

            await username_field.fill(username)
            await password_field.fill(password)
            await wait_for(6000)

            await sign_in_button.click()
            await wait_for(6000)
            await page.screenshot(path="screenshots/screenshot1.png")

            password_field_2 = await page.wait_for_selector(
                '//input[@id="password"]', timeout=3000
            )
            await password_field_2.fill(password)
            await page.screenshot(path="screenshots/screenshot2.png")

            # Uncomment if you want to handle request interception for auth token
            # async def intercept_request(request):
            #     url = request.url
            #     if url == 'https://api.investopedia.com/simulator/graphql' and 'authorization' not in auth_header:
            #         auth_header['Authorization'] = request.headers.get('authorization', None)
            #         if auth_header['Authorization']:
            #             with open('./auth.json', 'w') as f:
            #                 json.dump(auth_header, f)

            # page.on('request', intercept_request)

            sign_in_button_2 = await page.wait_for_selector(
                '//input[@id="login"]', timeout=3000
            )
            await sign_in_button_2.click()
            await page.screenshot(path="screenshots/screenshot3.png")

            await page.wait_for_selector('//div[contains(@class,"v-main__wrap")]')

        except Exception as e:
            if not file_written:
                print("Error:", e)

        finally:
            await page.close()
            await browser.close()
            if file_written:
                print("Login successful")


if __name__ == "__main__":
    import os

    email = os.environ.get("INVESTOPEDIA_EMAIL")
    password = os.environ.get("INVESTOPEDIA_PASSWORD")
    asyncio.run(main(email, password))
