# fetch_data.py
# Pulls price history and key ratios for the watchlist via yfinance,
# and saves results to /data as JSON files plus a summary CSV.
# Run locally with: python scripts/fetch_data.py
# Also runs automatically via GitHub Actions on a schedule.
#
# SCOPE NOTE: yfinance gives price data and some ratios (P/E, P/B,
# market cap, dividend yield). It does not give NIM, GNPA, CAR or
# brokerage targets -- those need a separate pipeline added later.

import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

# ---- paths -----------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_PATH = os.path.join(ROOT_DIR, "watchlist.json")
DATA_DIR = os.path.join(ROOT_DIR, "data")
PRICES_DIR = os.path.join(DATA_DIR, "prices")
SUMMARY_CSV_PATH = os.path.join(DATA_DIR, "summary.csv")

# Ranges matching the dashboard spec: 1d, 1wk, 1mo, 3mo, 6mo, YTD, 1y, 3y
RANGE_CONFIG = {
    "1d": {"period": "1d", "interval": "5m"},
    "1wk": {"period": "5d", "interval": "15m"},
    "1mo": {"period": "1mo", "interval": "1d"},
    "3mo": {"period": "3mo", "interval": "1d"},
    "6mo": {"period": "6mo", "interval": "1d"},
    "ytd": {"period": "ytd", "interval": "1d"},
    "1y": {"period": "1y", "interval": "1d"},
    "3y": {"period": "3y", "interval": "1wk"},
}


def load_watchlist():
    # Reads watchlist.json and returns the list of tracked tickers.
    with open(WATCHLIST_PATH, "r") as f:
        config = json.load(f)
    return config["watchlist"]


def fetch_price_ranges(ticker_obj):
    # Fetch OHLC data for every range defined in RANGE_CONFIG.
    ranges_out = {}
    for range_key, params in RANGE_CONFIG.items():
        try:
            hist = ticker_obj.history(
                period=params["period"], interval=params["interval"]
            )
            if hist.empty:
                ranges_out[range_key] = []
                continue
            hist = hist.reset_index()
            date_col = "Date" if "Date" in hist.columns else "Datetime"
            hist[date_col] = hist[date_col].astype(str)
            ranges_out[range_key] = hist[
                [date_col, "Open", "High", "Low", "Close", "Volume"]
            ].to_dict(orient="records")
        except Exception as exc:
            print("  [warn] range failed: " + range_key + " -- " + str(exc))
            ranges_out[range_key] = []
    return ranges_out


def fetch_key_ratios(ticker_obj):
    # Pull whatever fundamental ratios yfinance exposes. Values will be
    # missing for many Indian mid or small caps -- this is expected and
    # should be backfilled by the scraping layer later.
    try:
        info = ticker_obj.info
    except Exception as exc:
        print("  [warn] info fetch failed: " + str(exc))
        info = {}

    return {
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_book": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "return_on_equity": info.get("returnOnEquity"),
        "return_on_assets": info.get("returnOnAssets"),
        "debt_to_equity": info.get("debtToEquity"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "business_summary": info.get("longBusinessSummary"),
        "website": info.get("website"),
        "country": info.get("country"),
        "full_time_employees": info.get("fullTimeEmployees"),
    }


def main():
    os.makedirs(PRICES_DIR, exist_ok=True)
    watchlist = load_watchlist()
    summary_rows = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    for entry in watchlist:
        ticker_symbol = entry["ticker"]
        print("Fetching " + ticker_symbol + " (" + entry["name"] + ")...")
        try:
            ticker_obj = yf.Ticker(ticker_symbol)
            ranges = fetch_price_ranges(ticker_obj)
            ratios = fetch_key_ratios(ticker_obj)
        except Exception as exc:
            print("  [error] skipping " + ticker_symbol + ": " + str(exc))
            continue

        record = {
            "ticker": ticker_symbol,
            "name": entry["name"],
            "sector": entry["sector"],
            "fetched_at": fetched_at,
            "ratios": ratios,
            "price_ranges": ranges,
        }

        out_path = os.path.join(PRICES_DIR, ticker_symbol.replace(".", "_") + ".json")
        with open(out_path, "w") as f:
            json.dump(record, f, indent=2)

        summary_rows.append(
            {
                "ticker": ticker_symbol,
                "name": entry["name"],
                "sector": entry["sector"],
                "current_price": ratios.get("current_price"),
                "trailing_pe": ratios.get("trailing_pe"),
                "price_to_book": ratios.get("price_to_book"),
                "market_cap": ratios.get("market_cap"),
                "52_week_high": ratios.get("52_week_high"),
                "52_week_low": ratios.get("52_week_low"),
                "fetched_at": fetched_at,
            }
        )

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(SUMMARY_CSV_PATH, index=False)
        print("Wrote summary for " + str(len(summary_rows)) + " tickers to " + SUMMARY_CSV_PATH)
    else:
        print("[warn] No data fetched for any ticker.")
        sys.exit(1)


if __name__ == "__main__":
    main()
