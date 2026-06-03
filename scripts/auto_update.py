import os
import re
import csv
import ssl
import json
import datetime
import urllib.request
from PIL import Image

# Import Excel compiler
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compile_to_excel import compile_reports

# Initialize SSL Context for HTTPS calls
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Load .env file if present (for local runs)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path) as _f:
        for _line in _f:
            if "=" in _line and not _line.startswith("#"):
                k, v = _line.strip().split("=", 1)
                os.environ.setdefault(k, v)

# API Key and Endpoints
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
PARSE_URL = "https://api.firecrawl.dev/v2/parse"

APPROVED_APPS = ["Garmin", "Fitbit", "Strava", "Healthy 365", "Google Fit"]

# Threshold maps
RUN_THRESHOLDS = [3.5, 7.0, 10.0, 15.0, 30.0, 40.0]
CYCLING_THRESHOLDS = [10.0, 20.0, 30.0, 45.0, 90.0, 120.0]
STEPS_THRESHOLDS = [45000, 55000, 65000, 75000, 95000, 115000]

def get_threshold(category, tier):
    if tier <= 0: return 0
    if category == "Run/Jog":
        return RUN_THRESHOLDS[tier - 1]
    elif category == "Cycling":
        return CYCLING_THRESHOLDS[tier - 1]
    elif category == "Steps":
        return STEPS_THRESHOLDS[tier - 1]
    return 0

def check_borderline(category, distance_km, steps):
    if category == "Run/Jog":
        for t in RUN_THRESHOLDS:
            if t * 0.95 <= distance_km <= t * 1.05:
                return True
    elif category == "Cycling":
        for t in CYCLING_THRESHOLDS:
            if t * 0.95 <= distance_km <= t * 1.05:
                return True
    elif category == "Steps":
        for t in STEPS_THRESHOLDS:
            if t * 0.95 <= steps <= t * 1.05:
                return True
    return False

def parse_duration_hours(dur_str):
    if not dur_str:
        return 0.0
    # Match pattern Xh Ym Zs
    match_hms = re.search(r'(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?', dur_str, re.IGNORECASE)
    if match_hms and any(match_hms.groups()):
        h = int(match_hms.group(1) or 0)
        m = int(match_hms.group(2) or 0)
        s = int(match_hms.group(3) or 0)
        return h + m/60.0 + s/3600.0
    # Match colon pattern e.g., 27:50 or 1:20:00
    match_colon = re.search(r'(?:(\d+):)?(\d+):(\d+)', dur_str)
    if match_colon:
        parts = [int(p) for p in match_colon.groups() if p is not None]
        if len(parts) == 3:
            return parts[0] + parts[1]/60.0 + parts[2]/3600.0
        elif len(parts) == 2:
            return parts[0]/60.0 + parts[1]/3600.0
    return 0.0

def calculate_pace_kmh(pace_str, is_mi, distance_km, duration_str):
    # Parse MM:SS or similar
    match = re.search(r'(\d+):(\d+)', pace_str or '')
    if match:
        mins = int(match.group(1))
        secs = int(match.group(2))
        total_mins = mins + secs / 60.0
        if total_mins > 0:
            if is_mi:
                return (60.0 / total_mins) * 1.60934
            else:
                return 60.0 / total_mins
    # Match speed e.g. 9.92 km/h
    match_speed = re.search(r'([\d\.]+)\s*(?:km/h|kph)', pace_str or '', re.IGNORECASE)
    if match_speed:
        return float(match_speed.group(1))
    
    # Calculate fallback speed if possible
    dur_hours = parse_duration_hours(duration_str)
    if dur_hours > 0 and distance_km > 0:
        return distance_km / dur_hours
        
    return 0.0

def verify_ocr_accuracy(category, distance_km, pace_kmh, duration_str):
    """Triple-check OCR accuracy: verify distance matches pace and duration."""
    dur_hours = parse_duration_hours(duration_str)
    if dur_hours > 0 and pace_kmh > 0:
        expected_distance = pace_kmh * dur_hours
        if distance_km > 0:
            diff_percent = abs(distance_km - expected_distance) / expected_distance * 100
            if diff_percent > 10:
                return False, f"Distance {distance_km:.2f}km differs {diff_percent:.1f}% from expected {expected_distance:.2f}km"
    return True, "Verified"

def allocate_points(category, distance_km, steps, pace_kmh):
    effective_category = category
    if category == "Run/Jog":
        # Only classify as Steps if BOTH pace < 6 km/h AND distance < 2 km
        if pace_kmh < 6.0 and distance_km < 2.0:
            effective_category = "Steps"
            
    points = 0
    tier = 0
    
    if effective_category == "Steps":
        if steps >= 115000: points, tier = 6, 6
        elif steps >= 95000: points, tier = 5, 5
        elif steps >= 75000: points, tier = 4, 4
        elif steps >= 65000: points, tier = 3, 3
        elif steps >= 55000: points, tier = 2, 2
        elif steps >= 45000: points, tier = 1, 1
    elif effective_category == "Run/Jog":
        if distance_km >= 40.0: points, tier = 6, 6
        elif distance_km >= 30.0: points, tier = 5, 5
        elif distance_km >= 15.0: points, tier = 4, 4
        elif distance_km >= 10.0: points, tier = 3, 3
        elif distance_km >= 7.0: points, tier = 2, 2
        elif distance_km >= 3.5: points, tier = 1, 1
    elif effective_category == "Cycling":
        if distance_km >= 120.0: points, tier = 6, 6
        elif distance_km >= 90.0: points, tier = 5, 5
        elif distance_km >= 45.0: points, tier = 4, 4
        elif distance_km >= 30.0: points, tier = 3, 3
        elif distance_km >= 20.0: points, tier = 2, 2
        elif distance_km >= 10.0: points, tier = 1, 1
        
    return points, tier, effective_category

def get_week_info(timestamp_str):
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            dt = datetime.datetime.strptime(timestamp_str, fmt)
            break
        except ValueError:
            continue
    else:
        dt = datetime.datetime.now()
        
    year, week_num, weekday = dt.isocalendar()
    monday = dt - datetime.timedelta(days=weekday - 1)
    sunday = monday + datetime.timedelta(days=6)
    return week_num, monday, sunday, dt

MONTH_WEEKS = {
    "2026-05": range(18, 23), "2026-06": range(23, 27),
    "2026-07": range(27, 31), "2026-08": range(31, 36),
    "2026-09": range(36, 40), "2026-10": range(40, 45),
    "2026-11": range(45, 49),
}

def get_report_dir(week_num):
    for month, weeks in MONTH_WEEKS.items():
        if week_num in weeks:
            return month
    return datetime.datetime.now().strftime("%Y-%m")

def get_month_weeks(week_num):
    """Return all week numbers in the same 4-week month as the given week."""
    for weeks in MONTH_WEEKS.values():
        if week_num in weeks:
            return list(weeks)
    return [week_num]

def read_report_rows(report_path):
    """Parse activity rows from an existing markdown report."""
    rows = []
    if not os.path.exists(report_path):
        return rows
    with open(report_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_strip = line.strip()
            if line_strip.startswith('|') and not line_strip.startswith('| :---') and not line_strip.startswith('| Date/Timestamp') and not line_strip.startswith('| Member'):
                parts = [p.strip() for p in line_strip.split('|')[1:-1]]
                if len(parts) >= 9:
                    try:
                        rows.append({
                            "timestamp": parts[0],
                            "profile": parts[1],
                            "category": parts[2],
                            "distance_km": float(parts[3]),
                            "steps": int(parts[4].replace(',', '')),
                            "points": int(parts[5]),
                            "app": parts[6],
                            "image_link": parts[7],
                            "status": parts[8]
                        })
                    except (ValueError, IndexError):
                        pass
    return rows

SCORING_START_WEEK = 22

def determine_pledges(week_num):
    """Determine each member's pledge from their first activity from Week 22 onwards."""
    month_dir = get_report_dir(week_num)
    weeks_in_month = get_month_weeks(week_num)
    pledges = {}  # profile -> "Steps" or "Distance"
    
    # Only consider weeks from scoring start onwards
    scoring_weeks = [wk for wk in weeks_in_month if wk >= SCORING_START_WEEK]
    
    all_rows = []
    for wk in scoring_weeks:
        path = f"Reports/{month_dir}/Week_{wk}_Report.md"
        all_rows.extend(read_report_rows(path))
    
    all_rows.sort(key=lambda x: x["timestamp"])
    
    for row in all_rows:
        name = row["profile"]
        if name not in pledges:
            cat = row["category"]
            if cat == "Steps":
                pledges[name] = "Steps"
            else:  # Run/Jog or Cycling
                pledges[name] = "Distance"
    return pledges

def download_image(file_id, output_path):
    url = f"https://lh3.googleusercontent.com/d/{file_id}"
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            content = response.read()
            if content[:15].lower().startswith(b'<!doctype') or content[:5].lower().startswith(b'<html'):
                # Fallback to uc?export=download
                url2 = f"https://drive.google.com/uc?export=download&id={file_id}"
                req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req2, context=ctx) as resp2:
                    content = resp2.read()
            with open(output_path, 'wb') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Failed to download image {file_id}: {e}")
        return False

def convert_jpg_to_pdf(jpg_path, pdf_path):
    try:
        image = Image.open(jpg_path)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(pdf_path, "PDF", resolution=100.0)
        return True
    except Exception as e:
        print(f"Failed to convert PDF: {e}")
        return False

def run_firecrawl_ocr(pdf_path):
    import requests
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}"
    }
    
    schema = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Category of the exercise (e.g. Running, Jogging, Cycling, Steps, Walking)."
            },
            "distance": {
                "type": "number",
                "description": "The raw distance number, e.g. 2.4, 6.03, 3.5. Use 0.0 if not present."
            },
            "distance_unit": {
                "type": "string",
                "description": "The unit of distance (e.g. mi, miles, km, meters). If not found, use Unknown."
            },
            "steps": {
                "type": "integer",
                "description": "The number of steps. If not found, use 0."
            },
            "duration": {
                "type": "string",
                "description": "Duration of the session, e.g. active time like 27:50, 27m 50s."
            },
            "pace": {
                "type": "string",
                "description": "Pace of the session, e.g. 11:35/mi, 6:16/km, 9.92 km/h."
            },
            "app": {
                "type": "string",
                "description": "Approved app source: Strava, Garmin, Fitbit, Healthy 365, Google Fit. If not one of these, specify the app name or Unknown."
            }
        },
        "required": ["category", "distance", "distance_unit", "steps", "duration", "pace", "app"]
    }

    with open(pdf_path, 'rb') as f:
        files = {
            "file": (os.path.basename(pdf_path), f, "application/pdf")
        }
        data = {
            "options": json.dumps({
                "formats": [
                    {
                        "type": "json",
                        "schema": schema,
                        "prompt": "Analyze the text to identify which of the approved apps (Google Fit, Strava, Garmin, Fitbit, Healthy 365) was used. Google Fit features terms like 'Active time', 'Move Minutes', 'Energy expended'. Strava features 'Avg Pace', 'Elevation Gain', 'Elevation'. Garmin uses Connect. Healthy 365 tracks Singapore national steps."
                    }
                ],
                "parsers": [
                    {
                        "type": "pdf",
                        "mode": "ocr"
                    }
                ]
            })
        }
        
        response = requests.post(PARSE_URL, headers=headers, files=files, data=data)
        try:
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}


def run_tesseract_ocr(image_path):
    """Fallback OCR using pytesseract when Firecrawl credits are exhausted.
    Accepts a .jpg or .pdf path; extracts text then parses structured fields."""
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    except ImportError:
        return {"success": False, "error": "pytesseract not installed. Run: pip install pytesseract"}

    try:
        img = Image.open(image_path.replace('.pdf', '.jpg'))
        text = pytesseract.image_to_string(img)
    except Exception as e:
        return {"success": False, "error": f"Tesseract OCR failed: {e}"}

    # Parse structured fields from raw OCR text
    text_lower = text.lower()

    # Detect app
    app = "Unknown"
    if "strava" in text_lower:
        app = "Strava"
    elif "garmin" in text_lower or "connect" in text_lower:
        app = "Garmin"
    elif "fitbit" in text_lower:
        app = "Fitbit"
    elif "healthy 365" in text_lower or "healthy365" in text_lower:
        app = "Healthy 365"
    elif "google fit" in text_lower or "fit.google" in text_lower:
        app = "Google Fit"

    # Detect category
    category = "Walking"
    if "run" in text_lower or "jog" in text_lower:
        category = "Running"
    elif "cycl" in text_lower or "bike" in text_lower or "ride" in text_lower:
        category = "Cycling"
    elif "step" in text_lower:
        category = "Steps"

    # Extract distance
    dist_match = re.search(r'([\d]+[.,]\d+)\s*(km|mi|miles?|kilometers?)', text, re.IGNORECASE)
    distance = float(dist_match.group(1).replace(',', '.')) if dist_match else 0.0
    distance_unit = dist_match.group(2).lower() if dist_match else "km"

    # Extract steps
    steps_match = re.search(r'([\d,]+)\s*steps', text, re.IGNORECASE)
    steps = int(steps_match.group(1).replace(',', '')) if steps_match else 0

    # Extract duration (formats: 27:50, 1:20:00, 27m 50s, 1h 20m)
    dur_match = re.search(r'(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2}|\d+h\s*\d+m|\d+m\s*\d+s)', text, re.IGNORECASE)
    duration = dur_match.group(0) if dur_match else ""

    # Extract pace
    pace_match = re.search(r"(\d{1,2}:\d{2})\s*/\s*(km|mi)", text, re.IGNORECASE)
    if not pace_match:
        pace_match = re.search(r"([\d.]+)\s*km/h", text, re.IGNORECASE)
    pace = pace_match.group(0) if pace_match else ""

    return {
        "success": True,
        "data": {
            "json": {
                "category": category,
                "distance": distance,
                "distance_unit": distance_unit,
                "steps": steps,
                "duration": duration,
                "pace": pace,
                "app": app
            }
        }
    }

def scrape_google_sheet_csv(sheet_id="1NdwkcROXpgWg9hJAPNd1qC6SeGnexH63Y9Qa9KkjkLc", gid=None):
    """Fallback: fetch Google Sheet as CSV export (no API key needed for public sheets)."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid is not None:
        url += f"&gid={gid}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            raw = response.read().decode("utf-8")
        reader = csv.DictReader(raw.splitlines())
        rows = []
        for r in reader:
            ts = r.get("Timestamp") or r.get("timestamp")
            prof = r.get("Profile") or r.get("Name") or r.get("name")
            img = r.get("Image Link") or r.get("image_link") or r.get("Link")
            if ts:
                rows.append({"Timestamp": ts, "Profile": prof, "Image Link": img})
        return rows
    except Exception as e:
        print(f"Google Sheet CSV fallback failed: {e}")
        return None


def update_markdown_report(report_path, week_num, monday, sunday, new_rows_data):
    existing_rows = []
    existing_notes = []
    
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith('|') and not line_strip.startswith('| :---') and not line_strip.startswith('| Date/Timestamp') and not line_strip.startswith('| Member'):
                parts = [p.strip() for p in line_strip.split('|')[1:-1]]
                if len(parts) >= 9:
                    existing_rows.append({
                        "timestamp": parts[0],
                        "profile": parts[1],
                        "category": parts[2],
                        "distance_km": float(parts[3]),
                        "steps": int(parts[4].replace(',', '')),
                        "points": int(parts[5]),
                        "app": parts[6],
                        "image_link": parts[7],
                        "status": parts[8]
                    })
            if line_strip.startswith('- **'):
                existing_notes.append(line_strip)
    
    for nr in new_rows_data:
        if not any(r["timestamp"] == nr["timestamp"] for r in existing_rows):
            existing_rows.append({
                "timestamp": nr["timestamp"],
                "profile": nr["profile"],
                "category": nr["category"],
                "distance_km": nr["distance_km"],
                "steps": nr["steps"],
                "points": nr["points"],
                "app": nr["app"],
                "image_link": f"[View]({nr['image_link']})" if not nr['image_link'].startswith('[') else nr['image_link'],
                "status": nr["status"]
            })
            time_str = nr["timestamp"].split(' ')[1]
            note_line = f"- **{nr['profile']} ({time_str}):** {nr['note']}"
            existing_notes.append(note_line)
    
    existing_rows.sort(key=lambda x: x["timestamp"])
    
    new_content = []
    new_content.append(f"# Strides in Sync 2026 - Week {week_num} Report\n")
    if week_num < 22:
        new_content.append("> ⚠️ **Trial Period** — Scores are indicative only and not officially recorded.\n")
    new_content.append(f"**Period:** {monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}\n")
    new_content.append("| Date/Timestamp | Profile | Category | Distance (km) | Steps | Points | App | Image Link | Status |")
    new_content.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for r in existing_rows:
        new_content.append(f"| {r['timestamp']} | {r['profile']} | {r['category']} | {r['distance_km']:.2f} | {r['steps']:,} | {r['points']} | {r['app']} | {r['image_link']} | {r['status']} |")
    
    # Determine pledges for the month
    # Write report first so determine_pledges can read it
    dirname = os.path.dirname(report_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    
    # Temporarily write so pledge detection can read this week's data
    temp_content = '\n'.join(new_content) + '\n'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(temp_content)
    
    pledges = determine_pledges(week_num)
    
    # Build cumulative from scoring start week onwards only
    MEMBER_ORDER = ['CRX', 'Jeremy', 'Kai Fong', 'Chee', 'Surya', 'Kelvin', 'Ron', 'Chun Chieh']
    month_dir = get_report_dir(week_num)
    weeks_in_month = get_month_weeks(week_num)
    scoring_weeks = [wk for wk in weeks_in_month if wk >= SCORING_START_WEEK]
    
    all_month_rows = []
    for wk in scoring_weeks:
        path = f"Reports/{month_dir}/Week_{wk}_Report.md"
        all_month_rows.extend(read_report_rows(path))
    
    member_cum = {m: {'steps': 0, 'run_dist': 0.0, 'cycle_dist': 0.0} for m in MEMBER_ORDER}
    
    for r in all_month_rows:
        name = r["profile"]
        if name not in member_cum:
            member_cum[name] = {'steps': 0, 'run_dist': 0.0, 'cycle_dist': 0.0}
        pledge = pledges.get(name)
        # Only accumulate pledged activities
        if pledge == "Steps" and r["category"] == "Steps":
            member_cum[name]['steps'] += r["steps"]
        elif pledge == "Distance":
            if r["category"] == "Run/Jog":
                member_cum[name]['run_dist'] += r["distance_km"]
            elif r["category"] == "Cycling":
                member_cum[name]['cycle_dist'] += r["distance_km"]

    # Calculate points from cumulative totals
    scoring_active = week_num >= 22
    member_pts = {}
    for name in MEMBER_ORDER:
        d = member_cum[name]
        s_pts = r_pts = c_pts = 0
        if scoring_active:
            pledge = pledges.get(name)
            if pledge == "Steps":
                s_pts, _, _ = allocate_points("Steps", 0, d['steps'], 99)
            elif pledge == "Distance":
                r_pts, _, _ = allocate_points("Run/Jog", d['run_dist'], 0, 99)
                c_pts, _, _ = allocate_points("Cycling", d['cycle_dist'], 0, 99)
        member_pts[name] = {'steps_pts': s_pts, 'run_pts': r_pts, 'cycle_pts': c_pts,
                            'total': s_pts + r_pts + c_pts}

    total_points = sum(member_pts[name]['total'] for name in MEMBER_ORDER)

    final_content = []
    final_content.extend(new_content)
    final_content.append("\n---")
    final_content.append(f"**Total Points Accumulated:** {total_points}\n")

    month_name = datetime.datetime.strptime(month_dir, "%Y-%m").strftime("%B %Y")
    final_content.append(f"## Month-to-Date Cumulative Summary ({month_name} — Through Week {week_num})\n")
    final_content.append("> **Scoring method:** Cumulative month-to-date total per pledged category → tier applied **once** to the total. Non-pledged activities are excluded from scoring.\n")
    final_content.append("| Member | Total Steps | Total Distance Jogging/Running (km) | Total Distance Cycling (km) | Steps Points | Run/Jog Points | Cycling Points | Total Points |")
    final_content.append("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for name in MEMBER_ORDER:
        d = member_cum[name]
        p = member_pts[name]
        final_content.append(f"| {name} | {d['steps']:,} | {d['run_dist']:.2f} | {d['cycle_dist']:.2f} | {p['steps_pts']} | {p['run_pts']} | {p['cycle_pts']} | {p['total']} |")

    # Pledge summary line
    pledge_parts = []
    for name in MEMBER_ORDER:
        if name in pledges:
            pledge_parts.append(f"{name} → {pledges[name]}")
    if pledge_parts:
        final_content.append(f"\n**Pledges:** {' | '.join(pledge_parts)}")

    final_content.append("\n---\n")
    final_content.append("**Notes:**")
    for n in existing_notes:
        final_content.append(n)
    
    final_content_str = '\n'.join(final_content) + '\n'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(final_content_str)
    print(f"Updated report: {report_path}")

def main():
    # Read existing responses to skip duplicates
    processed_timestamps = set()
    csv_path = "responses.csv"
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skip header if present
            header = next(reader, None)
            for row in reader:
                if row:
                    processed_timestamps.add(row[0])
                    
    # Scrape Google Sheet — try Firecrawl first, fall back to direct CSV export
    rows = None
    if FIRECRAWL_API_KEY:
        headers = {
            "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "url": "https://docs.google.com/spreadsheets/d/1NdwkcROXpgWg9hJAPNd1qC6SeGnexH63Y9Qa9KkjkLc/edit?usp=sharing",
            "formats": ["json"],
            "jsonOptions": {
                "prompt": "Extract the rows from the 'Form Responses 1' tab. Each row must include Timestamp, Profile, and Image Link."
            },
            "maxAge": 0
        }
        
        print("Scraping Google Sheet via Firecrawl...")
        req = urllib.request.Request(SCRAPE_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                resp_data = response.read().decode("utf-8")
                parsed = json.loads(resp_data)
                
                if parsed.get("success"):
                    raw_json = parsed.get("data", {}).get("json", [])
                    if isinstance(raw_json, dict) and "rows" in raw_json:
                        rows = raw_json["rows"]
                    elif isinstance(raw_json, dict) and "form_responses" in raw_json:
                        rows = raw_json["form_responses"]
                    elif isinstance(raw_json, list):
                        rows = raw_json
                else:
                    print("Firecrawl scrape failed:", parsed.get("error", "unknown"))
        except Exception as e:
            print(f"Firecrawl API error: {e}")

    if rows is None:
        print("Falling back to direct Google Sheet CSV export...")
        rows = scrape_google_sheet_csv()
        if rows is None:
            print("All scraping methods failed. Exiting.")
            return
        
    print(f"Scraped {len(rows)} responses.")
    
    # Filter for new responses
    new_responses = []
    for r in rows:
        ts = r.get("Timestamp") or r.get("timestamp")
        prof = r.get("Profile") or r.get("profile") or r.get("Name") or r.get("name")
        img_link = r.get("Image Link") or r.get("image_link") or r.get("Link") or r.get("link")
        
        if ts and ts not in processed_timestamps:
            new_responses.append({
                "timestamp": ts,
                "profile": prof,
                "image_link": img_link
            })
            
    if not new_responses:
        print("No new form responses found. Leaderboard is up to date.")
        return
        
    print(f"Processing {len(new_responses)} new responses...")
    
    os.makedirs("temp_images", exist_ok=True)
    
    new_rows_by_week = {} # week_num -> list of dicts
    
    # Open CSV in append mode
    with open(csv_path, 'a', newline='', encoding='utf-8') as f_csv:
        writer = csv.writer(f_csv)
        
        for nr in new_responses:
            ts = nr["timestamp"]
            profile = nr["profile"]
            img_link = nr["image_link"]
            
            print(f"\nProcessing submission from {profile} at {ts}...")
            
            # Extract Drive ID
            drive_id_match = re.search(r'(?:id=|\/d\/)([A-Za-z0-9_-]+)', img_link)
            if not drive_id_match:
                print(f"Skipping submission due to invalid Drive link: {img_link}")
                continue
                
            drive_id = drive_id_match.group(1)
            
            jpg_path = f"temp_images/{drive_id}.jpg"
            pdf_path = f"temp_images/{drive_id}.pdf"
            
            # Download and Convert
            if not download_image(drive_id, jpg_path):
                continue
            if not convert_jpg_to_pdf(jpg_path, pdf_path):
                continue
                
            # Perform OCR — try Firecrawl first, fall back to Tesseract
            ocr_res = None
            if FIRECRAWL_API_KEY:
                print(f"Calling Firecrawl OCR parse for {profile}...")
                ocr_res = run_firecrawl_ocr(pdf_path)
                if not ocr_res.get("success"):
                    print(f"Firecrawl OCR failed: {ocr_res.get('error', 'unknown')}. Trying Tesseract fallback...")
                    ocr_res = None

            if ocr_res is None:
                print(f"Using Tesseract OCR for {profile}...")
                ocr_res = run_tesseract_ocr(jpg_path)

            if not ocr_res.get("success"):
                print(f"All OCR methods failed for {profile}: {ocr_res}")
                continue
                
            info = ocr_res.get("data", {}).get("json", {})
            print(f"OCR results extracted: {info}")
            
            raw_cat = info.get("category", "Unknown")
            raw_dist = float(info.get("distance") or 0.0)
            dist_unit = info.get("distance_unit", "km").lower()
            raw_steps = int(info.get("steps") or 0)
            raw_dur = info.get("duration", "")
            raw_pace = info.get("pace", "")
            extracted_app = info.get("app", "Unknown")
            
            # Conversions
            is_mi = dist_unit in ("mi", "miles", "mile") or "mi" in raw_pace
            if is_mi:
                distance_km = round(raw_dist * 1.60934, 2)
            else:
                distance_km = round(raw_dist, 2)
                
            pace_kmh = calculate_pace_kmh(raw_pace, is_mi, distance_km, raw_dur)
            
            # Triple-check OCR accuracy
            ocr_valid, ocr_msg = verify_ocr_accuracy(raw_cat, distance_km, pace_kmh, raw_dur)
            if not ocr_valid:
                print(f"OCR verification warning for {profile}: {ocr_msg}")
                status = "Flagged"
            
            # Category alignment
            category = "Steps"
            if "run" in raw_cat.lower() or "jog" in raw_cat.lower():
                category = "Run/Jog"
            elif "cycl" in raw_cat.lower() or "bike" in raw_cat.lower():
                category = "Cycling"
            elif "walk" in raw_cat.lower() or "step" in raw_cat.lower():
                category = "Steps"
                
            # Score assignment
            points, tier, effective_cat = allocate_points(category, distance_km, raw_steps, pace_kmh)
            
            # Determine App source & approval
            is_approved = extracted_app in APPROVED_APPS
            status = "Verified"
            if not is_approved:
                status = "Committee Approval Required"
            elif check_borderline(category, distance_km, raw_steps):
                status = "Flagged"
                
            # Date/Week mapping
            week_num, monday, sunday, dt = get_week_info(ts)
            
            # Scoring starts Week 22 onwards
            if week_num < 22:
                points, tier = 0, 0

            # Generate note details
            note = generate_note_text(profile, dt, category, raw_dist, dist_unit, distance_km, raw_steps, raw_pace, pace_kmh, points, tier, extracted_app, status)
            
            # Write to CSV
            writer.writerow([ts, profile, img_link])
            f_csv.flush()
            
            entry = {
                "timestamp": ts,
                "profile": profile,
                "category": effective_cat,
                "distance_km": distance_km,
                "steps": raw_steps,
                "points": points,
                "app": extracted_app,
                "image_link": img_link,
                "status": status,
                "note": note
            }
            
            if week_num not in new_rows_by_week:
                new_rows_by_week[week_num] = []
            new_rows_by_week[week_num].append(entry)
            
    # Process reports for each affected week
    for week_num, entries in new_rows_by_week.items():
        # Get period monday and sunday
        _, monday, sunday, _ = get_week_info(entries[0]["timestamp"])
        report_dir = get_report_dir(week_num)
        
        # Path to update (Reports folder only)
        sub_report = f"Reports/{report_dir}/Week_{week_num}_Report.md"
        
        update_markdown_report(sub_report, week_num, monday, sunday, entries)
        
    # Recompile Excel Sheets
    print("\nRegenerating Excel tallies and leaderboards...")
    compile_reports("Reports", "Strides_in_Sync_2026_Compilation.xlsx", "Reports/Members")
    
    # Cleanup temp images
    print("Cleaning up temporary local image files...")
    for f in os.listdir("temp_images"):
        file_path = os.path.join("temp_images", f)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")
            
    print("Auto-update process completed successfully!")

def generate_note_text(profile, dt, category, raw_dist, dist_unit, distance_km, raw_steps, raw_pace, pace_kmh, points, tier, app, status):
    is_mi = dist_unit in ("mi", "miles", "mile") or "mi" in raw_pace
    is_approved = app in APPROVED_APPS
    
    note = ""
    if category == "Run/Jog":
        if is_mi:
            note += f"{raw_dist} miles converted to {distance_km:.2f} km. "
            note += f"Pace {raw_pace} converted to {pace_kmh:.2f} km/h. "
        else:
            note += f"OCR extraction: {distance_km:.2f} km Run ({pace_kmh:.2f} km/h). "
            
        if points > 0:
            note += f"Qualifies for Tier {tier} ({get_threshold(category, tier)} km). "
        else:
            note += f"Below Tier 1 threshold or pace below 6 km/h. "
            
    elif category == "Cycling":
        note += f"OCR extraction: {distance_km:.2f} km Cycling. "
        if points > 0:
            note += f"Qualifies for Tier {tier} ({get_threshold(category, tier)} km). "
        else:
            note += f"Below Tier 1 threshold. "
            
    elif category == "Steps":
        if raw_steps > 0:
            note += f"OCR extraction: {raw_steps:,} steps. "
            if points > 0:
                note += f"Qualifies for Tier {tier} ({get_threshold(category, tier):,} steps). "
            else:
                note += f"Below Tier 1 threshold. "
        else:
            note += f"OCR extraction: {raw_dist:.2f} km Walk. Below 2.0 km threshold; classified as Steps. 0 points assigned. "
            
    if status == "Flagged":
        note += f"Flagged: within 5% of Tier threshold. "
    elif status == "Committee Approval Required":
        note += f"Flagged: unapproved tracking application. "
        
    note += f"App identified: {app} ({'Approved' if is_approved else 'Unapproved'})."
    return note

if __name__ == "__main__":
    main()
