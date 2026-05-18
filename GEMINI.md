# Strides in Sync 2026 - Project Instructions

## Context
This project tracks exercise sessions (Running, Jogging, Cycling, and Steps) and allocates points based on a Tiered Points System.

**Data Source:** [Google Sheets - Strides in Sync 2026 (Responses)](https://docs.google.com/spreadsheets/d/1NdwkcROXpgWg9hJAPNd1qC6SeGnexH63Y9Qa9KkjkLc/edit?usp=sharing)

## Data Processing & Update Workflow
1.  **Routine Data Extraction (The "Sweet Spot"):**
    *   For weekly updates, use `firecrawl_scrape` with `formats: ["json"]` to fetch data from Google Sheets.
    *   **Prompt:** "Extract the rows from the 'Form Responses 1' tab. Each row must include Timestamp, Profile, and Image Link."
    *   **Rationale:** This provides browser-rendered reliability at a low credit cost (5 credits), avoiding the high expenditure of the `firecrawl_agent`.
2.  **Escalation Protocol (If Scrape Fails):**
    *   Only use `firecrawl_agent` if `firecrawl_scrape` returns empty results or if you suspect data exists on other tabs not captured by the initial scrape.
    *   Always check the `scrapeId` metadata to ensure the status code is 200.

3.  **Visual Extraction & OCR:**
    *   Always verify the **Total Duration** against the **Distance** and **Pace** to prevent OCR hallucinations.
    *   Look for a '1' preceding the decimal (e.g., distinguishing between 1.49 and 15.01).
    *   Check for 'mi' vs 'km' labels explicitly.

4.  **Image Fetch Failure Workflow:**
    *   If `firecrawl_scrape` fails on a Google Drive link (e.g., 403 Forbidden), download the image locally using `run_shell_command` with `Invoke-WebRequest`.
    *   Process the local image using `firecrawl_parse` for OCR.
    *   **Mandatory Cleanup:** Delete the local image file immediately after the report is updated.

## Verification Protocol (Borderline Flagging)
| Tier | Steps | Run/Jog (km) | Cycling (km) | Points |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 45,000 | 3.5 | 10 | 1 |
| 2 | 55,000 | 7 | 20 | 2 |
| 3 | 65,000 | 10 | 30 | 3 |
| 4 | 75,000 | 15 | 45 | 4 |
| 5 | 95,000 | 30 | 90 | 5 |
| 6 | 115,000 | 40 | 120 | 6 |

*Note: Run/Jog requires a minimum pace of 6 km/h to qualify for these tiers.*

## Standard Reporting Format
Weekly reports must use the following table structure:
| Date/Timestamp | Profile | Category | Distance (km) | Points | Image Link | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| YYYY-MM-DD HH:MM | Name | Run/Jog | 0.00 | 0 | [Link] | Verified/Flagged |

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
