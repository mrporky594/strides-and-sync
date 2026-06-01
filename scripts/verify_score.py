"""Quick tier verification utility. Run with: python scripts/verify_score.py <category> <value>
Example: python scripts/verify_score.py run 33.80
         python scripts/verify_score.py steps 94600
"""
import sys

TIERS = {
    "run": [3.5, 7.0, 10.0, 15.0, 30.0, 40.0],
    "cycling": [10.0, 20.0, 30.0, 45.0, 90.0, 120.0],
    "steps": [45000, 55000, 65000, 75000, 95000, 115000],
}

def get_tier(category, value):
    thresholds = TIERS.get(category)
    if not thresholds:
        return 0, 0
    tier = 0
    for i, t in enumerate(thresholds):
        if value >= t:
            tier = i + 1
    return tier, tier

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/verify_score.py <run|cycling|steps> <value>")
        sys.exit(1)
    cat = sys.argv[1].lower()
    val = float(sys.argv[2])
    tier, pts = get_tier(cat, val)
    print(f"{cat.title()} | Value: {val} | Tier: {tier} | Points: {pts}")
