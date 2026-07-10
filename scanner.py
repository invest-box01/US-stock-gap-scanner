import yfinance as yf
from symbols import get_symbols

GAP_THRESHOLD = 20
LOOKBACK_DAYS = 5
BATCH_SIZE = 100

def clean_symbol(symbol):
    return symbol.replace(".", "-").strip()

def scan_batch(symbols):
    results = []

    data = yf.download(
        tickers=" ".join(symbols),
        period="15d",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False
    )

    for symbol in symbols:
        try:
            df = data[symbol].dropna()

            if len(df) < LOOKBACK_DAYS + 1:
                continue

            recent = df.tail(LOOKBACK_DAYS + 1)

            for i in range(1, len(recent)):
                prev_close = recent["Close"].iloc[i - 1]
                today_open = recent["Open"].iloc[i]

                gap = ((today_open - prev_close) / prev_close) * 100

                if gap >= GAP_THRESHOLD:
                    date = recent.index[i].strftime("%Y-%m-%d")
                    results.append((symbol, date, gap))
                    break

        except Exception:
            continue

    return results

def main():
    raw_symbols = get_symbols()
    symbols = [clean_symbol(s) for s in raw_symbols]

    print(f"取得銘柄数: {len(symbols)}")
    print("20%以上GU銘柄をスキャン開始")

    all_results = []

    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        print(f"Scanning {i + 1} - {i + len(batch)} / {len(symbols)}")

        results = scan_batch(batch)
        all_results.extend(results)

    print("")
    print("===== 直近5営業日以内 20%以上GU銘柄 =====")

    if not all_results:
        print("該当銘柄なし")
    else:
        for symbol, date, gap in sorted(all_results, key=lambda x: x[2], reverse=True):
            print(f"{symbol} | {date} | Gap: {gap:.2f}%")

        print(f"")
        print(f"合計: {len(all_results)}銘柄")

if __name__ == "__main__":
    main()