
from playwright.sync_api import sync_playwright

URL = "https://www.nashville.gov/departments/community-review/boards/community-review-board/meetings"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page()
    response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)

    print("HTTP status:", response.status if response else "No response")
    print("Page title:", page.title())

    print("Meeting links found:")
    links = page.locator('a[href*="/meetings/"]').all()

    for link in links[:10]:
        print(link.get_attribute("href"))

    browser.close()
