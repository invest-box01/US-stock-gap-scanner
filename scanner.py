import yfinance as yf
from symbols import get_symbols

GAP_THRESHOLD = 20
LOOKBACK_DAYS = 5
BATCH_SIZE = 100

MIN_MARKET_CAP = 3_000_000_000
MIN_AVG_VOLUME_30D = 700_000


def clean_symbol(symbol):
    return symbol.replace(".", "-").strip()


def get_market_cap(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        return info.get("market_cap", None)
    except Exception:
        return None


def scan_batch(symbols):
    results = []

    data = yf.download(
        tickers=" ".join(symbols),
        period="45d",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False
    )

    for symbol in symbols:
        try:
            df = data[symbol].dropna()

            if len(df) < 31:
                continue

            avg_volume_30d = df["Volume"].tail(30).mean()

            if avg_volume_30d < MIN_AVG_VOLUME_30D:
                continue

            market_cap = get_market_cap(symbol)

            if market_cap is None or market_cap < MIN_MARKET_CAP:
                continue

            recent = df.tail(LOOKBACK_DAYS + 1)

            for i in range(1, len(recent)):
                prev_close = recent["Close"].iloc[i - 1]
                today_open = recent["Open"].iloc[i]

                if prev_close <= 0:
                    continue

                gap = ((today_open - prev_close) / prev_close) * 100

                if gap >= GAP_THRESHOLD:
                    date = recent.index[i].strftime("%Y-%m-%d")
                    results.append(
                        (symbol, date, gap, market_cap, avg_volume_30d)
                    )
                    break

        except Exception:
            continue

    return results


def main():
    raw_symbols = get_symbols()
    symbols = [clean_symbol(s) for s in raw_symbols]

    print(f"取得銘柄数: {len(symbols)}")
    print("条件:")
    print("・直近5営業日以内に20%以上GU")
    print("・時価総額3Bドル以上")
    print("・30日平均出来高70万株以上")
    print("スキャン開始")

    all_results = []

    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        print(f"Scanning {i + 1} - {i + len(batch)} / {len(symbols)}")

        results = scan_batch(batch)
        all_results.extend(results)

    print("")
    print("===== 条件一致銘柄 =====")

    if not all_results:
        print("該当銘柄なし")
    else:
        for symbol, date, gap, market_cap, avg_volume_30d in sorted(
            all_results,
            key=lambda x: x[2],
            reverse=True
        ):
            print(
                f"{symbol} | {date} | "
                f"Gap: {gap:.2f}% | "
                f"MarketCap: ${market_cap / 1_000_000_000:.2f}B | "
                f"AvgVol30D: {avg_volume_30d:,.0f}"
            )

        print("")
        print(f"合計: {len(all_results)}銘柄")


if __name__ == "__main__":
    main()