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
    *   **Triple-check verification:** For every entry, verify:
        1. **Distance matches pace and duration** — Calculate expected distance from pace × duration. If OCR distance differs by >10%, flag for manual review.
        2. **Unit labels are explicit** — Confirm 'mi', 'km', 'miles', or 'kilometers' is visible. If missing, assume based on app defaults.
        3. **Decimal point is correct** — Distinguish between 1.49 and 14.9 by checking surrounding digits and context.

5.  **Image Fetch Failure Workflow:**
    *   If `firecrawl_scrape` fails on a Google Drive link (e.g., 403 Forbidden), download the image locally using `run_shell_command` with `Invoke-WebRequest`.
    *   Process the local image using `firecrawl_parse` for OCR.
    *   **Mandatory Cleanup:** Delete the local image file immediately after the report is updated.

## Verification Protocol (Borderline Flagging)
*   Flag any entry for **Human Verification** if the distance is within **5%** of a higher Tier threshold.
*   *Example:* A run of 3.4 km is within 5% of the 3.5 km Tier 1 threshold and must be flagged.
*   If a user provides a manual correction, the manual value takes precedence over the OCR data.

## Tier Assignment Verification
**MANDATORY STEP:** Before assigning points to any entry, **always verify the cumulative total against the tier table**:
1. Calculate the cumulative total for the member's pledged category.
2. Cross-reference the total against the tier thresholds in the Points Tier System table.
3. Assign points based on the **highest tier the cumulative total qualifies for** (≥ threshold).
4. **Do not assume** — always check the exact threshold values.
5. **For manual processing:** Run `python scripts/verify_score.py <run|cycling|steps> <value>` to confirm tier assignment before writing to the report.
6. **Always recalculate totals from scratch** — never increment/decrement existing totals. Sum all individual member points fresh each time to derive Total Points Accumulated.
*   *Example:* 94,600 steps is below Tier 5 (95,000), so it qualifies for Tier 4 (75,000) = 4 pts, not 5 pts.

## Points Tier System
| Tier | Steps | Run/Jog (km) | Cycling (km) | Points |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 45,000 | 3.5 | 10 | 1 |
| 2 | 55,000 | 7 | 20 | 2 |
| 3 | 65,000 | 10 | 30 | 3 |
| 4 | 75,000 | 15 | 45 | 4 |
| 5 | 95,000 | 30 | 90 | 5 |
| 6 | 115,000 | 40 | 120 | 6 |

*Note: Run/Jog classification requires **both** pace ≥ 6 km/h **AND** distance ≥ 2 km. If either condition fails, entry is classified as Steps.*

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
Every weekly report **must** include a cumulative summary section that aggregates all activity **within that week only**. The table **must** list members in the following fixed order:

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

#### Pledge System (One Pledge Per Month)
- **1 month = 4 weeks** for consistency purposes.
- Each member pledges **one activity type per month**:
  - **Steps pledge:** Walk and Jog activities count towards cumulative step totals.
  - **Distance pledge:** Walk, Jog, and Cycle activities count towards cumulative distance totals (km).
- A member's **first submitted activity** in the month determines their pledge for that month.
- Activities that do **not** fall under the member's pledged category are recorded as **non-pledged** and are **excluded from the total score**.
- **Total Points** = points from the member's single pledged category only.
- All qualifying activities within the pledged category are **cumulatively added within each week** and scored against the tier system.
- **Cumulative resets each week** — totals do not carry forward to the next week.

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

### Scoring Start
- **Weeks 18–21:** Data recorded for tracking only. All points = 0.
- **Week 22 onwards:** Official scoring begins. Cumulative totals are counted **from Week 22 onwards only**. A member's first entry in Week 22 determines their pledge for the month.
