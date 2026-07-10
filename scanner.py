import yfinance as yf
from symbols import get_symbols

def gap_percent(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="7d")

        if len(hist) < 2:
            return None

        prev_close = hist["Close"].iloc[-2]
        today_open = hist["Open"].iloc[-1]

        return ((today_open - prev_close) / prev_close) * 100

    except Exception:
        return None

def main():
    symbols = get_symbols()

    print(f"取得銘柄数: {len(symbols)}")

    # 動作確認のため最初の5銘柄だけ表示
    for symbol in symbols[:5]:
        print(symbol)

if __name__ == "__main__":
    main()
