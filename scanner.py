import yfinance as yf

def gap_percent(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="7d")

    if len(hist) < 2:
        return None

    prev_close = hist["Close"].iloc[-2]
    today_open = hist["Open"].iloc[-1]

    gap = ((today_open - prev_close) / prev_close) * 100
    return gap

def main():
    symbol = "AAPL"

    gap = gap_percent(symbol)

    if gap is None:
        print("データ取得失敗")
    else:
        print(f"{symbol} Gap: {gap:.2f}%")

if __name__ == "__main__":
    main()
