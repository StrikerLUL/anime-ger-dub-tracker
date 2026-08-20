import asyncio
from playwright.async_api import async_playwright
import os

async def test_tooltip():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        file_path = f"file://{os.path.abspath('Anime Synchro Tracker v11.0.1.html')}"

        # print console messages
        page.on("console", lambda msg: print(f"Browser console [{msg.type}]: {msg.text}"))

        await page.goto(file_path)

        # Wait for data to load and render
        await page.wait_for_timeout(2000)

        html = await page.content()
        # print the inner HTML of #contentArea
        el = await page.locator("#contentArea").inner_html()
        print("contentArea: ", el)

        cards = await page.locator(".anime-card").all()
        print(f"Cards found: {len(cards)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_tooltip())
