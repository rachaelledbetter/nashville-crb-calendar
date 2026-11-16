
from pathlib import Path
from datetime import datetime, timezone

OUTPUT = Path("crb-meetings.ics")

def generate_calendar():
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Nashville CRB Calendar//EN
CALSCALE:GREGORIAN
X-WR-CALNAME:Nashville Community Review Board
X-WR-TIMEZONE:America/Chicago
DTSTAMP:{timestamp}
END:VCALENDAR
"""

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Created {OUTPUT}")

if __name__ == "__main__":
    generate_calendar()
