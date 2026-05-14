import asyncio
from playwright.async_api import async_playwright
import os

async def test_tooltip():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        file_path = f"file://{os.path.abspath('Anime Synchro Tracker v11.0.1.html')}"
        await page.goto(file_path)

        # Wait for data to load and render
        await page.wait_for_timeout(2000)

        # Check the title attribute of the first anime card
        cards = await page.locator(".anime-card").all()
        if cards:
            title_attr = await cards[0].get_attribute("title")
            if title_attr:
                print(f"Success: Tooltip title attribute found: '{title_attr}'")

                # Basic check to see if it contains parts of a tooltip
                if "|" in title_attr and "Episoden" in title_attr:
                    print("Success: Tooltip contains expected formatting ('|' and 'Episoden').")
                else:
                    print(f"Error: Tooltip does not contain expected formatting. Actual title: {title_attr}")
                    exit(1)
            else:
                print("Error: No title attribute found on anime card.")
                exit(1)
        else:
            print("Warning: No anime cards found to test tooltip.")
            exit(1)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_tooltip())
