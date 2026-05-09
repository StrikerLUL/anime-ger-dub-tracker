import asyncio
from playwright.async_api import async_playwright
import os

async def test_shortcuts():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        file_path = f"file://{os.path.abspath('Anime Synchro Tracker v11.0.1.html')}"
        await page.goto(file_path)

        # Test '/' shortcut
        await page.keyboard.press("/")

        # Verify search input is focused
        is_focused = await page.evaluate("document.activeElement.id === 'searchInput'")
        if is_focused:
            print("Success: '/' focused the search input.")
        else:
            print("Error: '/' did not focus the search input.")

        # Test 'Escape' unfocuses input
        await page.keyboard.press("Escape")
        is_focused_after_esc = await page.evaluate("document.activeElement.id === 'searchInput'")
        if not is_focused_after_esc:
            print("Success: 'Escape' removed focus from the search input.")
        else:
            print("Error: 'Escape' did not remove focus.")

        # Test 'Escape' closes modal
        # Wait for data to load and render
        await page.wait_for_timeout(2000)

        # Click the first anime card to open the modal
        cards = await page.locator(".anime-card").all()
        if cards:
            await cards[0].click()
            await page.wait_for_timeout(500)

            # Check if modal is open
            is_modal_active = await page.evaluate("document.getElementById('detailsModal').classList.contains('active')")
            if is_modal_active:
                print("Modal opened successfully.")

                # Press Escape
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(500)

                is_modal_active_after_esc = await page.evaluate("document.getElementById('detailsModal').classList.contains('active')")
                if not is_modal_active_after_esc:
                    print("Success: 'Escape' closed the modal.")
                else:
                    print("Error: 'Escape' did not close the modal.")
            else:
                print("Warning: Modal did not open, skipping modal test.")
        else:
            print("Warning: No anime cards found to test modal, skipping modal test.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_shortcuts())
