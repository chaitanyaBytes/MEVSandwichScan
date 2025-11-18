import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from price_fetcher import fetch_prices_usd

SOL_MINT = "So11111111111111111111111111111111111111112"
DEFAULT_ANALYSIS_PATH = Path("profit_analysis.json")
DEFAULT_BOT_PNL_PATH = Path("pnl_report_per_bot.json")


def load_sandwiches(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Sandwich file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    sandwiches = data.get("sandwiches") or data
    if not isinstance(sandwiches, list):
        raise ValueError("Input file must contain a list or {sandwiches: [...]}")
    return sandwiches


def get_bot(s: Dict[str, Any]) -> str:
    return (
        s.get("attack_metadata", {}).get("bot_wallet")
        or s.get("bot_address")
        or s.get("front_run", {}).get("signer", "unknown")
    )


def determine_flow(s: Dict[str, Any]) -> Tuple[str, str, float, float]:
    fr = s["front_run"]
    br = s["back_run"]
    if fr["token_in"] == br["token_out"]:
        return (
            fr["token_in"],
            br["token_out"],
            float(fr["amount_in"]),
            float(br["amount_out"]),
        )
    if fr["token_out"] == br["token_in"]:
        return (
            fr["token_out"],
            br["token_in"],
            float(fr["amount_out"]),
            float(br["amount_in"]),
        )
    raise ValueError("Front/back run directions do not align")


def compute_profit(
    s: Dict[str, Any], prices_usd: Dict[str, float], sol_price: float, sid: int
) -> Dict[str, Any]:
    token_spent, token_received, amount_spent, amount_received = determine_flow(s)
    profit_raw = amount_received - amount_spent
    price_usd = prices_usd.get(token_received, 0.0)
    profit_usd = profit_raw * price_usd
    profit_sol = profit_usd / sol_price if sol_price else 0.0

    return {
        "sandwich_id": sid,
        "bot": get_bot(s),
        "token_spent": token_spent,
        "amount_spent": amount_spent,
        "token_received": token_received,
        "amount_received": amount_received,
        "profit_token": token_received,
        "profit_raw": profit_raw,
        "profit_usd": profit_usd,
        "profit_sol": profit_sol,
        "front_run": s.get("front_run"),
        "victim": s.get("victim"),
        "back_run": s.get("back_run"),
    }


def summarize_results(
    results: List[Dict[str, Any]], sol_price: float
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "total_sandwiches": len(results),
        "profitable_count": len([r for r in results if r["profit_raw"] > 0]),
        "loss_count": len([r for r in results if r["profit_raw"] <= 0]),
        "max_profit_usd": max((r["profit_usd"] for r in results), default=0.0),
        "max_profit_sol": max((r["profit_sol"] for r in results), default=0.0),
        "total_profit_usd": sum(r["profit_usd"] for r in results),
        "total_profit_sol": sum(r["profit_sol"] for r in results),
        "sol_price_usd": sol_price,
    }

    per_bot = defaultdict(lambda: {"count": 0, "profit_usd": 0.0, "profit_sol": 0.0})
    for r in results:
        row = per_bot[r["bot"]]
        row["count"] += 1
        row["profit_usd"] += r["profit_usd"]
        row["profit_sol"] += r["profit_sol"]

    summary["top_bots"] = sorted(
        (
            {
                "bot": bot,
                "sandwich_count": data["count"],
                "profit_usd": data["profit_usd"],
                "profit_sol": data["profit_sol"],
            }
            for bot, data in per_bot.items()
        ),
        key=lambda row: row["profit_usd"],
        reverse=True,
    )[:5]

    return summary


def print_summary(summary: Dict[str, Any]) -> None:
    print(f"Sandwiches analyzed: {summary['total_sandwiches']}")
    print(
        f"Profitable: {summary['profitable_count']} | Losing: {summary['loss_count']}"
    )
    print(
        f"Total profit: {summary['total_profit_usd']:.4f} USD | "
        f"{summary['total_profit_sol']:.4f} SOL"
    )
    print(
        f"Best sandwich: {summary['max_profit_usd']:.4f} USD | "
        f"{summary['max_profit_sol']:.4f} SOL"
    )

    if summary["top_bots"]:
        print("Top bots by USD profit:")
        for bot in summary["top_bots"]:
            print(
                f"  {bot['bot'][:16]}... | {bot['profit_usd']:.4f} USD "
                f"({bot['profit_sol']:.4f} SOL) across {bot['sandwich_count']} sandwiches"
            )


def save_results(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved {path}")


def run_profit_analysis(
    sandwich_file: Path,
    output_analysis: Path = DEFAULT_ANALYSIS_PATH,
    output_bot: Path = DEFAULT_BOT_PNL_PATH,
):
    print("=" * 70)
    print("PROFIT ANALYSIS")
    print("=" * 70)
    print(f"Loading sandwiches from {sandwich_file}")

    sandwiches = load_sandwiches(sandwich_file)
    if not sandwiches:
        print("No sandwiches found.")
        return

    mints = set()
    for s in sandwiches:
        for tx_key in ("front_run", "back_run", "victim"):
            tx = s.get(tx_key)
            if tx:
                mints.add(tx["token_in"])
                mints.add(tx["token_out"])

    prices_usd = fetch_prices_usd(list(mints))
    sol_price = prices_usd.get(SOL_MINT, 0.0)
    if not sol_price:
        print("[WARN] SOL price missing; SOL profits stay zero.")

    print(
        f"Fetched {len(prices_usd)} prices from Jupiter. SOL price = {sol_price:.4f} USD."
    )

    results: List[Dict[str, Any]] = []

    for idx, s in enumerate(sandwiches, start=1):
        try:
            results.append(compute_profit(s, prices_usd, sol_price, idx))
        except Exception as exc:
            print(f"[WARN] Skipped sandwich #{idx}: {exc}")

    results.sort(key=lambda r: r["profit_usd"], reverse=True)

    summary = summarize_results(results, sol_price)
    print_summary(summary)

    save_results(output_analysis, results)
    bot_summary = {row["bot"]: row for row in summary["top_bots"]}
    save_results(output_bot, bot_summary)


def main():
    sandwich_file = Path("sandwich_attacks.json").expanduser()
    analysis_output = DEFAULT_ANALYSIS_PATH.expanduser()
    pnl_output = DEFAULT_BOT_PNL_PATH.expanduser()
    try:
        run_profit_analysis(sandwich_file, analysis_output, pnl_output)
    except Exception as exc:
        print(f"[ERROR] Universal PnL run failed: {exc}")


if __name__ == "__main__":
    main()
