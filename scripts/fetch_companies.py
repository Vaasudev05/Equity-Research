# fetch_companies.py
# Pulls the full list of NSE listed equities (symbol plus company name)
# from the NSE public archive and saves it as companies.json at the repo
# root. This powers the dashboard search box so it covers all NSE
# stocks, not just a curated watchlist.
#
# Run locally with: python scripts/fetch_companies.py
# Also runs weekly via .github/workflows/update-companies.yml
# (listings do not change daily, so weekly is enough).

import json
import os
import sys

import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(ROOT_DIR, "companies.json")

NSE_EQUITY_LIST_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/csv,application/csv,*/*",
}


def main():
    print("Fetching NSE equity list...")
    try:
        response = requests.get(NSE_EQUITY_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        print("[error] could not fetch NSE equity list: " + str(exc))
        print("[note] NSE sometimes blocks non-browser requests. If this")
        print("[note] keeps failing, the URL or headers may need updating.")
        sys.exit(1)

    lines = response.text.strip().split("\n")
    if len(lines) < 2:
        print("[error] unexpected empty response from NSE")
        sys.exit(1)

    header = [h.strip() for h in lines[0].split(",")]
    try:
        symbol_idx = header.index("SYMBOL")
        name_idx = header.index("NAME OF COMPANY")
    except ValueError:
        print("[error] expected columns not found in NSE CSV header: " + str(header))
        sys.exit(1)

    companies = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) <= max(symbol_idx, name_idx):
            continue
        symbol = parts[symbol_idx].strip()
        name = parts[name_idx].strip()
        if not symbol or not name:
            continue
        companies.append({"ticker": symbol + ".NS", "name": name})

    with open(OUTPUT_PATH, "w") as f:
        json.dump({"companies": companies, "count": len(companies)}, f, indent=2)

    print("Wrote " + str(len(companies)) + " companies to " + OUTPUT_PATH)


if __name__ == "__main__":
    main()
