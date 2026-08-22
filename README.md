# Personal Stock Research Dashboard — Step 2: Data Layer

This is the foundation layer discussed in chat: a free, self-updating script
that pulls price history + basic ratios for your watchlist and commits the
results back to this repo automatically, using GitHub Actions (free for
public repos).

## What this does right now
- Pulls price data for all ranges (1d, 1wk, 1mo, 3mo, 6mo, YTD, 1y, 3y)
- Pulls whatever fundamental ratios Yahoo Finance exposes (P/E, P/B, market
  cap, ROE, ROA, D/E, 52-week high/low)
- Saves one JSON file per stock to `data/prices/`, plus a `data/summary.csv`
  overview of the whole watchlist
- Re-runs automatically on weekdays after market close via GitHub Actions

## What this does NOT do yet (by design — see chat for the full roadmap)
- No NIM / GNPA / CAR / sector-specific ratios (needs financial-statement
  scraping or manual entry — Step 3)
- No brokerage consensus targets (no reliable free source exists)
- No AI insights / auditor's report analysis / PESTLE (Step 6 — the Claude
  API layer, triggered by document upload as discussed)
- No frontend yet — this only produces the data files a dashboard would read

## Setup (5 minutes)

1. **Create a new GitHub repo** (public, so Actions minutes are free) and
   push this folder's contents to it.

2. **No secrets needed for this step** — yfinance doesn't require an API key.

3. **Enable Actions** if prompted (Settings → Actions → allow workflows).

4. **Test it manually first**: go to the "Actions" tab → "Update Stock Data"
   workflow → "Run workflow" button. This runs it once immediately instead
   of waiting for the schedule, so you can confirm it works.

5. **Check the results**: after the run finishes (~1-2 min), you should see
   new/updated files under `data/prices/` and `data/summary.csv` committed
   automatically to your repo.

6. From then on, it re-runs automatically every weekday at 4:00 PM IST
   (adjust the cron schedule in `.github/workflows/update-data.yml` if you
   want a different time — cron times are in UTC).

## Running it locally (optional, for testing/debugging)

```bash
pip install -r requirements.txt
python scripts/fetch_data.py
```

## Editing your watchlist

Add/remove companies in `watchlist.json`. Ticker format is the NSE symbol
plus `.NS` (e.g. `RELIANCE.NS`). For BSE-only listings, use `.BO` instead.

## Next steps (per the build plan discussed in chat)
- Step 3: add Screener.in scraping (or manual entry) for NIM/GNPA/CAR/D-E
  and 3-year quarterly/yearly financials with YoY/QoQ coloring
- Step 4: Supabase or Google Sheets for structured storage + history
- Step 5: (this step, done)
- Step 6: Claude API layer — auditor's report extraction (auto on upload),
  PESTLE rubric with bulk upload + "Inadequate Information" handling (auto
  on upload), and AI financial insights (manual, user-selected period)
- Step 7: React frontend (Vercel-hosted, free) reading from your data store
