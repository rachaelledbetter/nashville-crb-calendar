
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
from pathlib import Path
import re
import hashlib

SOURCE_URL = "https://www.nashville.gov/departments/community-review/boards/community-review-board/meetings"
OUTPUT = Path("crb-meetings.ics")
TIMEZONE = ZoneInfo("America/Chicago")

def escape_ics(value):
    return (str(value).replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;"))

def parse_time(value):
    value = re.sub(r"\.", "", value).strip().upper()
    return datetime.strptime(value, "%I:%M %p").time()

def extract_meeting(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    text = page.locator("body").inner_text()

    date_match = re.search(
        r"\bDate\s+([A-Za-z]+ \d{1,2}, 20\d{2})", text
    )

    time_match = re.search(
        r"\bTime\s+(\d{1,2}:\d{2}\s*[ap]\.?m\.?)"
        r"\s*[-–]\s*"
        r"(\d{1,2}:\d{2}\s*[ap]\.?m\.?)",
        text,
        re.IGNORECASE
    )

    if not date_match or not time_match:
        print(f"Skipping (date/time missing): {url}")
        return None

    date = datetime.strptime(date_match.group(1), "%B %d, %Y").date()
    start_time = parse_time(time_match.group(1))
    end_time = parse_time(time_match.group(2))

    start = datetime.combine(date, start_time, TIMEZONE)
    end = datetime.combine(date, end_time, TIMEZONE)

    if end <= start:
        end += timedelta(days=1)

    title_match = re.search(
        r"(Community Review Board Meeting(?:,\s*[A-Za-z]+ \d{1,2}, 20\d{2})?)",
        text
    )

    title = "Community Review Board Meeting"
    if "Special" in text[:1000]:
        title = "CRB Special Meeting"

    uid = hashlib.sha256(url.encode()).hexdigest()[:24] + "@nashville-crb"

    return {
        "uid": uid,
        "title": title,
        "start": start,
        "end": end,
        "url": url
    }

def generate_calendar():
    meetings = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        response = page.goto(
            SOURCE_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        if not response or response.status != 200:
            raise RuntimeError("Could not load Nashville.gov meetings page.")

        links = set()

        for link in page.locator('a[href*="/meetings/"]').all():
            href = link.get_attribute("href")
            if not href:
                continue

            url = urljoin(SOURCE_URL, href)

            if re.search(r"/meetings/[^/?#]+/20\d{2}-\d{2}-\d{2}", url):
                links.add(url.split("?")[0])

        print(f"Found {len(links)} meeting links")

        for url in sorted(links):
            try:
                meeting = extract_meeting(page, url)
                if meeting:
                    meetings.append(meeting)
            except Exception as error:
                print(f"Error reading {url}: {error}")

        browser.close()

    if not meetings:
        raise RuntimeError("No meetings found. Calendar not overwritten.")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Nashville CRB//Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Nashville Community Review Board"
    ]

    for meeting in meetings:
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{meeting['uid']}",
            f"DTSTAMP:{timestamp}",
            f"DTSTART:{meeting['start'].astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{meeting['end'].astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{escape_ics(meeting['title'])}",
            f"DESCRIPTION:{escape_ics('Official meeting details: ' + meeting['url'])}",
            f"URL:{meeting['url']}",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")

    OUTPUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")

    print(f"Saved {len(meetings)} meetings to {OUTPUT}")

if __name__ == "__main__":
    generate_calendar()
