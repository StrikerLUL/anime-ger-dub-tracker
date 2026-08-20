import asyncio
from playwright.async_api import async_playwright
import os

async def test_tooltip():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        file_path = f"file://{os.path.abspath('Anime Synchro Tracker v11.0.1.html')}"

        # print console messages
        page.on("pageerror", lambda err: print(f"Page error: {err.message}"))

        await page.goto(file_path)
        await page.wait_for_timeout(2000)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_tooltip())
