# Strides in Sync 2026 - Project Instructions

## Context
This project tracks exercise sessions (Running, Jogging, Cycling, and Steps) and allocates points based on a Tiered Points System.

**Data Source:** [Google Sheets - Strides in Sync 2026 (Responses)](https://docs.google.com/spreadsheets/d/1NdwkcROXpgWg9hJAPNd1qC6SeGnexH63Y9Qa9KkjkLc/edit?usp=sharing)

## Data Processing Rules
1.  **Scope of Points:**
    *   Points should only be counted from **Week 21 onwards**.
    *   Entries prior to Week 21 should be recorded for tracking but assigned 0 points for the official tally.
2.  **Classification Logic:**
    *   **Run/Jog:** Must be **> 2.0 km** AND **faster than 6.0 km/h**.
    *   **Steps:** If the above criteria are not met, the entry is counted as Steps.
2.  **Unit Conversions:**
    *   1 Mile = 1.60934 Kilometers.
    *   Pace (min/mi) to Speed (km/h): `(60 / pace_in_miles) * 1.60934`.
3.  **Visual Extraction Guidelines:**
    *   Always verify the **Total Duration** against the **Distance** and **Pace** to prevent OCR hallucinations.
    *   Look for a '1' preceding the decimal (e.g., distinguishing between 1.49 and 15.01).
    *   Check for 'mi' vs 'km' labels explicitly.
4.  **Verification Protocol (Borderline Flagging):**
    *   Flag any entry for **Human Verification** if the distance is within **5%** of a higher Tier threshold.
    *   *Example:* A run of 3.4 km is within 5% of the 3.5 km Tier 1 threshold and must be flagged.
    *   If a user provides a manual correction, the manual value takes precedence over the OCR data.

5.  **Image Fetch Failure Workflow:**
    *   If `web_fetch` fails to extract data from a Google Drive/Image link, download the image locally using `Invoke-WebRequest`.
    *   Process the local image using `read_file` for OCR and data extraction.
    *   **Mandatory Cleanup:** Delete the local image file immediately after the report is updated.

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

