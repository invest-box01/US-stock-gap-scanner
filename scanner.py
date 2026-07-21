import yfinance as yf
from symbols import get_symbols

GAP_THRESHOLD = 15
LOOKBACK_DAYS = 5
BATCH_SIZE = 100

MIN_MARKET_CAP = 3_000_000_000
MIN_AVG_VOLUME_30D = 500_000
MIN_PRICE = 5
MIN_VOLUME_MULTIPLE = 1.5


def clean_symbol(symbol):
    return symbol.replace(".", "-").strip()


def get_market_cap(symbol):
    try:
        ticker = yf.Ticker(symbol)

        try:
            cap = ticker.fast_info.get("market_cap")
            if cap:
                return cap
        except Exception:
            pass

        try:
            info = ticker.get_info()
            cap = info.get("marketCap")
            if cap:
                return cap
        except Exception:
            pass

        return None

    except Exception:
        return None


def scan_batch(symbols):
    results = []
    missing_marketcap = []

    stats = {
        "checked": 0,
        "gap_hit": 0,
        "volume_pass": 0,
        "price_pass": 0,
        "market_cap_pass": 0,
        "market_cap_missing": 0,
    }

    data = yf.download(
        tickers=" ".join(symbols),
        period="45d",
        auto_adjust=False,
        interval="1d",
        group_by="ticker",
        threads=True,
        progress=False
    )

    for symbol in symbols:
        try:
            stats["checked"] += 1
            df = data[symbol].dropna()

            if len(df) < 31:
                continue

            recent = df.tail(LOOKBACK_DAYS + 1)
            gap_found = None
            gap_date = None
            gap_day_volume = None

            for i in range(1, len(recent)):
                prev_close = recent["Close"].iloc[i - 1]
                today_open = recent["Open"].iloc[i]
                today_low = recent["Low"].iloc[i]
                today_volume = recent["Volume"].iloc[i]

                if prev_close <= 0:
                    continue

                gap = ((today_open - prev_close) / prev_close) * 100

                if gap >= GAP_THRESHOLD and today_low > prev_close:
                    gap_found = gap
                    gap_date = recent.index[i].strftime("%Y-%m-%d")
                    gap_day_volume = today_volume
                    break

            if gap_found is None:
                continue

            stats["gap_hit"] += 1

            avg_volume_30d = df["Volume"].tail(30).mean()

            if avg_volume_30d < MIN_AVG_VOLUME_30D:
                continue

            stats["volume_pass"] += 1

            if gap_day_volume < avg_volume_30d * MIN_VOLUME_MULTIPLE:
                continue

            current_price = df["Close"].iloc[-1]

            if current_price < MIN_PRICE:
                continue

            stats["price_pass"] += 1

            market_cap = get_market_cap(symbol)

            if market_cap is None:
                stats["market_cap_missing"] += 1
                missing_marketcap.append(
                    (
                        symbol,
                        gap_date,
                        gap_found,
                        current_price,
                        avg_volume_30d,
                        gap_day_volume,
                    )
                )
                continue

            if market_cap < MIN_MARKET_CAP:
                continue

            stats["market_cap_pass"] += 1

            results.append(
                (
                    symbol,
                    gap_date,
                    gap_found,
                    market_cap,
                    avg_volume_30d,
                    gap_day_volume,
                    current_price,
                )
            )

        except Exception:
            continue

    return results, stats, missing_marketcap


def main():
    raw_symbols = get_symbols()
    symbols = [clean_symbol(s) for s in raw_symbols]

    print(f"取得銘柄数: {len(symbols)}")
    print("条件:")
    print("・直近5営業日以内に15%以上GU")
    print("・窓を維持: 当日の安値が前日終値より上")
    print("・株価5USD以上")
    print("・時価総額3Bドル以上")
    print("・30日平均出来高50万株以上")
    print("・GU当日出来高が30日平均の1.5倍以上")
    print("スキャン開始")

    all_results = []
    all_missing = []

    total_stats = {
        "checked": 0,
        "gap_hit": 0,
        "volume_pass": 0,
        "price_pass": 0,
        "market_cap_pass": 0,
        "market_cap_missing": 0,
    }

    for i in range(0, len(symbols), BATCH_SIZE):
        batch = symbols[i:i + BATCH_SIZE]
        print(f"Scanning {i + 1} - {i + len(batch)} / {len(symbols)}")

        results, stats, missing = scan_batch(batch)
        all_results.extend(results)
        all_missing.extend(missing)

        for key in total_stats:
            total_stats[key] += stats[key]

    print("")
    print("===== 集計 =====")
    print(f"チェック銘柄数: {total_stats['checked']}")
    print(f"15%以上GUかつ窓維持銘柄: {total_stats['gap_hit']}")
    print(f"30日平均出来高50万株以上: {total_stats['volume_pass']}")
    print(f"株価5USD以上: {total_stats['price_pass']}")
    print(f"時価総額取得失敗: {total_stats['market_cap_missing']}")
    print(f"時価総額3B以上: {total_stats['market_cap_pass']}")

    print("")
    print("===== 条件一致銘柄 =====")

    if not all_results:
        print("該当銘柄なし")
    else:
        for symbol, date, gap, market_cap, avg_volume_30d, gap_day_volume, current_price in sorted(
            all_results,
            key=lambda x: x[2],
            reverse=True
        ):
            volume_multiple = gap_day_volume / avg_volume_30d

            print(
                f"{symbol} | {date} | "
                f"Gap: {gap:.2f}% | "
                f"Price: ${current_price:.2f} | "
                f"MarketCap: ${market_cap / 1_000_000_000:.2f}B | "
                f"AvgVol30D: {avg_volume_30d:,.0f} | "
                f"GapDayVol: {gap_day_volume:,.0f} | "
                f"VolMultiple: {volume_multiple:.2f}x"
            )

        print("")
        print(f"合計: {len(all_results)}銘柄")

    print("")
    print("===== 時価総額取得失敗 =====")

    if not all_missing:
        print("なし")
    else:
        for symbol, date, gap, price, avgvol, gapvol in sorted(
            all_missing,
            key=lambda x: x[2],
            reverse=True
        ):
            volume_multiple = gapvol / avgvol

            print(
                f"{symbol} | {date} | "
                f"Gap: {gap:.2f}% | "
                f"Price: ${price:.2f} | "
                f"AvgVol30D: {avgvol:,.0f} | "
                f"GapDayVol: {gapvol:,.0f} | "
                f"VolMultiple: {volume_multiple:.2f}x"
            )


if __name__ == "__main__":
    main()