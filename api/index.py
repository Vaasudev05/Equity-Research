# api/index.py
# Single Vercel Python entrypoint (Vercel requires a recognized
# entrypoint filename such as api/index.py -- separate arbitrary files
# under /api are not auto-detected as functions).
#
# Handles three request types via a mode query parameter:
#   GET /api/index?mode=ratios&ticker=TICKER.NS
#   GET /api/index?mode=prices&ticker=TICKER.NS&range=6mo
#   GET /api/index?mode=news&company=Company+Name
#
# All fetch live -- nothing is cached or pre-generated, this runs fresh
# on every request. Ratios/prices come from Yahoo Finance via yfinance.
# News comes from Google News RSS (free, no API key needed), fetched
# server-side here since browsers cannot call it directly (CORS).

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import json
import xml.etree.ElementTree as ET

import yfinance as yf
import requests

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


def build_ratios_response(ticker_symbol):
    ticker_obj = yf.Ticker(ticker_symbol)
    info = ticker_obj.info
    return {
        "ticker": ticker_symbol,
        "name": info.get("longName") or info.get("shortName"),
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


def build_prices_response(ticker_symbol, range_key):
    if range_key not in RANGE_CONFIG:
        return {"error": "invalid range", "rows": []}

    params = RANGE_CONFIG[range_key]
    ticker_obj = yf.Ticker(ticker_symbol)
    hist = ticker_obj.history(period=params["period"], interval=params["interval"])

    if hist.empty:
        return {"rows": [], "date_col": "Date"}

    hist = hist.reset_index()
    date_col = "Date" if "Date" in hist.columns else "Datetime"
    hist[date_col] = hist[date_col].astype(str)
    rows = hist[[date_col, "Open", "High", "Low", "Close", "Volume"]].to_dict(orient="records")
    return {"rows": rows, "date_col": date_col}


def build_news_response(company_name):
    search_query = quote(company_name + " share price NSE")
    url = "https://news.google.com/rss/search?q=" + search_query + "&hl=en-IN&gl=IN&ceid=IN:en"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item")[:15]:
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")
        source_el = item.find("source")

        title = title_el.text if title_el is not None else "Untitled"
        link = link_el.text if link_el is not None else None
        published = pubdate_el.text if pubdate_el is not None else None
        source = source_el.text if source_el is not None else None

        if not source and " - " in title:
            title, source = title.rsplit(" - ", 1)

        domain = ""
        if link:
            try:
                domain = link.split("/")[2]
            except Exception:
                domain = ""

        items.append({
            "title": title,
            "link": link,
            "source": source or domain,
            "published": published,
            "favicon": "https://www.google.com/s2/favicons?domain=" + domain + "&sz=64" if domain else None,
        })

    return {"items": items}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        mode = query.get("mode", [None])[0]
        ticker_symbol = query.get("ticker", [None])[0]
        range_key = query.get("range", ["6mo"])[0]
        company_name = query.get("company", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if mode == "news":
            if not company_name:
                self.wfile.write(json.dumps({"error": "missing company parameter", "items": []}).encode())
                return
            try:
                result = build_news_response(company_name)
            except Exception as exc:
                result = {"error": str(exc), "items": []}
            self.wfile.write(json.dumps(result).encode())
            return

        if not ticker_symbol or mode not in ("ratios", "prices"):
            self.wfile.write(json.dumps({"error": "missing or invalid mode/ticker parameters"}).encode())
            return

        try:
            if mode == "ratios":
                result = build_ratios_response(ticker_symbol)
            else:
                result = build_prices_response(ticker_symbol, range_key)
        except Exception as exc:
            result = {"error": str(exc)}

        self.wfile.write(json.dumps(result).encode())
        return
