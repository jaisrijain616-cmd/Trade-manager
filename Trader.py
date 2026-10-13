#!/usr/bin/env python3
import datetime
import sys
import time
from bs4 import BeautifulSoup
import colorama
from colorama import Fore, Style
import pandas as pd
import requests
import yfinance as yf

# Initialize colorama for colored terminal logs
colorama.init(autoreset=True)

# Finviz Screener URL (Targeting technical breakouts / high relative volume)
FINVIZ_SCREENER_URL = "https://finviz.com/screener.ashx?v=111&f=ta_highvol_volatile,sh_avgvol_o500&ft=4"


def fetch_finviz_stocks(limit: int = 5) -> list[str]:
    """Scrapes top stock tickers from Finviz based on technical screening criteria."""
    print(f"{Fore.CYAN}[*] Fetching top trading candidates from Finviz...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        response = requests.get(FINVIZ_SCREENER_URL, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"{Fore.RED}[!] Failed to fetch Finviz. HTTP Status: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        tickers = []

        # Find table rows containing stock data in the screener table
        # Finviz table rows usually have specific CSS classes or table structures
        table_rows = soup.find_all("tr", class_="styled-row")
        if not table_rows:
            # Fallback parsing for alternative table layouts on Finviz
            table_rows = soup.find_all("tr", valign="top")

        for row in table_rows:
            cols = row.find_all("td")
            if len(cols) > 2:
                # Ticker is typically found in the 2nd column of the screener results table
                ticker_candidate = cols[1].get_text(strip=True)
                if ticker_candidate.isalpha() and len(ticker_candidate) <= 5:
                    if ticker_candidate not in tickers:
                        tickers.append(ticker_candidate)

            if len(tickers) >= limit:
                break

        # Fallback default list if parsing gets blocked by Cloudflare/Anti-bot walls
        if not tickers:
            print(f"{Fore.YELLOW}[!] Finviz anti-bot protection triggered or layout changed. Using fallback high-momentum tickers.")
            tickers = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT"]

        print(f"{Fore.GREEN}[+] Identified tickers: {', '.join(tickers[:limit])}")
        return tickers[:limit]

    except Exception as e:
        print(f"{Fore.RED}[!] Error scraping Finviz: {e}")
        return ["NVDA", "TSLA", "AAPL", "AMD", "MSFT"]


def analyze_and_predict(ticker: str) -> dict:
    """Fetches historical data, calculates indicators, and projects a 7-day trend."""
    print(f"{Fore.CYAN}[*] Analyzing and generating 7-day outlook for {ticker}...")
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo")
        
        if df.empty or len(df) < 30:
            return None

        current_price = df["Close"].iloc[-1]
        
        # Calculate Simple Moving Averages (SMA)
        df["SMA_20"] = df["Close"].rolling(window=20).mean()
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        
        sma_20 = df["SMA_20"].iloc[-1]
        sma_50 = df["SMA_50"].iloc[-1]

        # Calculate basic daily returns and volatility for prediction bounds
        df["Return"] = df["Close"].pct_change()
        daily_volatility = df["Return"].std()
        recent_trend = (df["Close"].iloc[-1] - df["Close"].iloc[-10]) / df["Close"].iloc[-10]

        # 7-day projection heuristic based on momentum and volatility simulation
        projected_change = recent_trend * 0.4  
        target_price = current_price * (1 + projected_change)
        
        # Determine outlook recommendation
        if current_price > sma_20 and sma_20 > sma_50 and recent_trend > 0:
            signal = "BULLISH (Strong Momentum)"
        elif current_price < sma_20 and sma_20 < sma_50:
            signal = "BEARISH (Downward Trend)"
        else:
            signal = "NEUTRAL / CONSOLIDATING"

        # Generate 7-day simulated path
        forecast_days = []
        simulated_price = current_price
        step = (target_price - current_price) / 7
        
        for i in range(1, 8):
            simulated_price += step + (current_price * daily_volatility * 0.1 * (1 if i % 2 == 0 else -1))
            forecast_days.append(round(simulated_price, 2))

        return {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "signal": signal,
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "seven_day_forecast": forecast_days,
            "projected_change_pct": round(projected_change * 100, 2)
        }

    except Exception as e:
        print(f"{Fore.RED}[!] Error analyzing {ticker}: {e}")
        return None


def main():
    print(f"{Fore.YELLOW}=== FINVIZ TECHNICAL TRADING & 7-DAY PREDICTOR ==={Style.RESET_ALL}\n")
    print(f"{Fore.MAGENTA}[!] Disclaimer: Educational tool only. Not financial advice.{Style.RESET_ALL}\n")

    # Step 1: Scrape candidates from Finviz
    tickers = fetch_finviz_stocks(limit=4)
    
    results = []
    for t in tickers:
        data = analyze_and_predict(t)
        if data:
            results.append(data)
        time.sleep(1) # Polite scraping delay

    # Step 2: Display Output Results
    print(f"\n{Fore.GREEN}=== TOP TRADE PREDICTIONS (NEXT 7 DAYS) ===")
    for res in results:
        print(f"\n{Fore.YELLOW}Ticker: {res['ticker']}{Style.RESET_ALL}")
        print(f"  Current Price       : ${res['current_price']}")
        print(f"  Technical Outlook   : {res['signal']}")
        print(f"  20-day / 50-day SMA : ${res['sma_20']} / ${res['sma_50']}")
        print(f"  Projected 7D Change : {res['projected_change_pct']}%")
        print(f"  7-Day Price Path    : {res['seven_day_forecast']}")
    
    print(f"\n{Fore.GREEN}=== ANALYSIS COMPLETE ===\n")


if __name__ == "__main__":
    main()