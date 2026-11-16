
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
from pathlib import Path
import re
import hashlib

SOURCE_URL = "https://www.nashville.gov/departments/community-review/boards/community-review-board/meetings"
OUTPUT = Path("crb-meetings.ics")
TIMEZONE = ZoneInfo("America/Chicago")

def escape_ics(text):
    return (str(text).replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;"))

def get_meeting_links():
  response = requests.get(
    SOURCE_URL,
    headers={
        "User-Agent": "Mozilla/5.0 (compatible; CRBCalendar/1.0)",
        "Accept": "text/html,application/xhtml+xml"
    },
    timeout=30
)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        url = urljoin(SOURCE_URL, a["href"])
        if re.search(r"/meetings/[^/?#]+/20\d{2}-\d{2}-\d{2}", url):
            links.add(url.split("?")[0])

    return sorted(links)

def parse_meeting(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    title = soup.find("h1")
    title = title.get_text(" ", strip=True) if title else "CRB Meeting"

    date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", url)
    if not date_match:
        return None

    date = datetime.strptime(date_match.group(1), "%Y-%m-%d")

    text = soup.get_text(" ", strip=True)

    time_match = re.search(
        r"(\d{1,2}:\d{2})\s*([AP]M)\s*(?:-|–|to)\s*"
        r"(\d{1,2}:\d{2})\s*([AP]M)",
        text,
        re.IGNORECASE
    )

    if not time_match:
        print(f"Skipping (time not found): {url}")
        return None

    start_str = f"{date.date()} {time_match[1]} {time_match[2]}"
    end_str = f"{date.date()} {time_match[3]} {time_match[4]}"

    start = datetime.strptime(start_str, "%Y-%m-%d %I:%M %p")
    end = datetime.strptime(end_str, "%Y-%m-%d %I:%M %p")

    start = start.replace(tzinfo=TIMEZONE)
    end = end.replace(tzinfo=TIMEZONE)

    if end <= start:
        end += timedelta(days=1)

    uid = hashlib.sha256(url.encode()).hexdigest()[:20] + "@nashville-crb"

    return {
        "uid": uid,
        "title": title,
        "start": start,
        "end": end,
        "url": url
    }

def generate_calendar():
    links = get_meeting_links()
    print(f"Found {len(links)} meeting links")

    meetings = []

    for url in links:
        try:
            meeting = parse_meeting(url)
            if meeting:
                meetings.append(meeting)
        except Exception as error:
            print(f"Error processing {url}: {error}")

    if not meetings:
        raise RuntimeError(
            "No meetings parsed. Check the Nashville.gov page format."
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Nashville CRB Calendar//EN",
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
