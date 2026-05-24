# Strides in Sync 2026 - Project Instructions

## Context
This project tracks exercise sessions (Running, Jogging, Cycling, and Steps) and allocates points based on a Tiered Points System.

**Data Source:** [Google Sheets - Strides in Sync 2026 (Responses)](https://docs.google.com/spreadsheets/d/1NdwkcROXpgWg9hJAPNd1qC6SeGnexH63Y9Qa9KkjkLc/edit?usp=sharing)

## Data Processing & Update Workflow
1.  **Routine Data Extraction (The "Sweet Spot"):**
    *   For weekly updates, use `firecrawl_scrape` with `formats: ["json"]` to fetch data from Google Sheets.
    *   **Prompt:** "Extract the rows from the 'Form Responses 1' tab. Each row must include Timestamp, Profile, and Image Link."
    *   **Rationale:** This provides browser-rendered reliability at a low credit cost (5 credits), avoiding the high expenditure of the `firecrawl_agent`.

2.  **Approved Tracking Applications:**
    *   **Approved Apps:** Garmin, Fitbit, Strava, Healthy 365, Google Fit.
    *   **Unapproved Apps:** Record the entry and calculate the score accordingly, but change the **Status** to "Committee Approval Required".
    *   **Detection:** Use visual markers (icons, layout, terminology) during OCR to identify the source app.

3.  **Escalation Protocol (If Scrape Fails):**
    *   Only use `firecrawl_agent` if `firecrawl_scrape` returns empty results or if you suspect data exists on other tabs not captured by the initial scrape.
    *   Always check the `scrapeId` metadata to ensure the status code is 200.

4.  **Visual Extraction & OCR:**
    *   Always verify the **Total Duration** against the **Distance** and **Pace** to prevent OCR hallucinations.
    *   Look for a '1' preceding the decimal (e.g., distinguishing between 1.49 and 15.01).
    *   Check for 'mi' vs 'km' labels explicitly.

5.  **Image Fetch Failure Workflow:**
    *   If `firecrawl_scrape` fails on a Google Drive link (e.g., 403 Forbidden), download the image locally using `run_shell_command` with `Invoke-WebRequest`.
    *   Process the local image using `firecrawl_parse` for OCR.
    *   **Mandatory Cleanup:** Delete the local image file immediately after the report is updated.

## Verification Protocol (Borderline Flagging)
*   Flag any entry for **Human Verification** if the distance is within **5%** of a higher Tier threshold.
*   *Example:* A run of 3.4 km is within 5% of the 3.5 km Tier 1 threshold and must be flagged.
*   If a user provides a manual correction, the manual value takes precedence over the OCR data.

## Points Tier System
| Tier | Steps | Run/Jog (km) | Cycling (km) | Points |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 45,000 | 3.5 | 10 | 1 |
| 2 | 55,000 | 7 | 20 | 2 |
| 3 | 65,000 | 10 | 30 | 3 |
| 4 | 75,000 | 15 | 45 | 4 |
| 5 | 95,000 | 30 | 90 | 5 |
| 6 | 115,000 | 40 | 120 | 6 |

*Note: Run/Jog requires a minimum pace of 6 km/h to qualify for these tiers.*

### Team Ranking Rules
*   **Weekly Ranking:** Team weekly ranking is based on the **average points** of team members.
*   **Rounding:** Average points are rounded to **2 decimal places**.

## Standard Reporting Format

### Part 1 — Raw Activity Log
Each weekly report begins with a raw activity log table:

| Date/Timestamp | Profile | Category | Distance (km) | Steps | Points | App | Image Link | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| YYYY-MM-DD HH:MM | Name | Category | 0.00 | 0 | 0 | App Name | [Link] | Verified/Flagged/Approval Required |

### Part 2 — Cumulative Summary Table
Every weekly report **must** include a cumulative summary section that aggregates all activity across the reporting period (weekly or monthly as applicable). The table **must** list members in the following fixed order:

> CRX → Jeremy → Kai Fong → Chee → Surya → Kelvin → Ron → Chun Chieh

| Member | Total Steps | Total Distance Jogging/Running (km) | Total Distance Cycling (km) | Steps Points | Run/Jog Points | Cycling Points | Total Points |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CRX | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Jeremy | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Kai Fong | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Chee | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Surya | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Kelvin | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Ron | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |
| Chun Chieh | 0 | 0.00 | 0.00 | 0 | 0 | 0 | 0 |

#### Category Consistency Rule (Points Lock)
- Each member may only earn points in **one category per month** (Steps, Run/Jog, or Cycling).
- The qualifying category is determined by the category the member submits **most consistently** within the month.
- Points columns for non-qualifying categories are still tracked as `0` for that member.
- **Total Points** = sum of points from the member's single qualifying category only.
- If a member switches categories mid-month without prior approval, flag the entry as **Committee Approval Required** and exclude those entries from the point tally until resolved.

## Reporting & Submission Schedule
Results are tabulated weekly and submitted to the committee. Data is stored in monthly folders (`./Reports/YYYY-MM/`) with weekly markdown files.

### Week Sequence (2026)
- **May:** Week 18, 19, 20, 21, 22
- **June:** Week 23, 24, 25, 26
- **July:** Week 27, 28, 29, 30
- **August:** Week 31, 32, 33, 34, 35
- **September:** Week 36, 37, 38, 39
- **October:** Week 40, 41, 42, 43, 44
- **November:** Week 45, 46, 47, 48
