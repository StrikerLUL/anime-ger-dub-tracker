import asyncio
from playwright.async_api import async_playwright
import os

async def test_filters():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        page = await context.new_page()

        file_path = f"file://{os.path.abspath('Anime Synchro Tracker v11.0.1.html')}"
        await page.goto(file_path)

        # Wait for data to load
        await page.wait_for_timeout(2000)

        # 1. Change some filters
        await page.fill("#searchInput", "Death Note")
        await page.select_option("#sortSelect", "title_asc")

        # Change tab
        await page.click("button[data-tab='aktuelle-dubs']")

        # Change page size
        await page.select_option("#pageSizeSelect", "48")

        # Give it a tiny bit of time for localStorage to save
        await page.wait_for_timeout(500)

        # Verify filters applied
        search_val = await page.input_value("#searchInput")
        sort_val = await page.input_value("#sortSelect")
        tab_active = await page.evaluate("document.querySelector('.tab-btn.active').dataset.tab")
        page_size_val = await page.input_value("#pageSizeSelect")

        print(f"Before reload: Search='{search_val}', Sort='{sort_val}', Tab='{tab_active}', PageSize='{page_size_val}'")

        # 2. Reload page
        await page.reload()
        await page.wait_for_timeout(2000)

        # 3. Verify filters are restored
        new_search_val = await page.input_value("#searchInput")
        new_sort_val = await page.input_value("#sortSelect")
        new_tab_active = await page.evaluate("document.querySelector('.tab-btn.active').dataset.tab")
        new_page_size_val = await page.input_value("#pageSizeSelect")

        print(f"After reload:  Search='{new_search_val}', Sort='{new_sort_val}', Tab='{new_tab_active}', PageSize='{new_page_size_val}'")

        if new_search_val == "Death Note" and new_sort_val == "title_asc" and new_tab_active == "aktuelle-dubs" and new_page_size_val == "48":
            print("Success: Filter settings were successfully persisted and restored.")
        else:
            print("Error: Filter settings were not properly restored.")
            exit(1)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_filters())