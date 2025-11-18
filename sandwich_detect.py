from datetime import datetime
import json
from pathlib import Path
from typing import List, Dict, Any

MAX_SLOT_GAP = 10
MIN_SLOT_GAP = 1
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)
DEFAULT_TRANSACTIONS_FILE = RESULTS_DIR / "transactions.json"
DEFAULT_OUTPUT_FILE = RESULTS_DIR / "sandwich_attacks.json"


def is_opposite_direction(a, b):
    return a["token_in"] == b["token_out"] and a["token_out"] == b["token_in"]


def is_same_direction(a, b):
    return a["token_in"] == b["token_in"] and a["token_out"] == b["token_out"]


def compute_price(tx):
    try:
        return tx["amount_out"] / tx["amount_in"]
    except Exception:
        return None


def detect_sandwiches(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    txs = sorted(transactions, key=lambda x: (x["slot"], x.get("tx_index", 99999)))

    sandwiches = []
    used_tx = set()

    for i, victim in enumerate(txs):
        victim_slot = victim["slot"]
        victim_signer = victim["signer"]

        potential_frontruns = []
        for j in range(i):
            fr = txs[j]

            if fr["signer"] == victim_signer:
                continue

            if victim_slot - fr["slot"] > 4:
                continue

            if not is_same_direction(fr, victim):
                continue

            potential_frontruns.append(fr)

        for frontrun in potential_frontruns:

            bot = frontrun["signer"]

            for k in range(i + 1, len(txs)):
                back = txs[k]

                if back["slot"] - victim_slot > 4:
                    break

                if back["signer"] != bot:
                    continue

                if not is_opposite_direction(back, victim):
                    continue

                sandwich = {
                    "front_run": frontrun,
                    "victim": victim,
                    "back_run": back,
                    "attack_metadata": {
                        "slot_gap_front_to_victim": victim["slot"] - frontrun["slot"],
                        "slot_gap_victim_to_backrun": back["slot"] - victim["slot"],
                        "slot_gap_front_to_backrun": back["slot"] - frontrun["slot"],
                        "token_pair": [victim["token_in"], victim["token_out"]],
                        "bot_wallet": bot,
                        "victim_wallet": victim_signer,
                        "is_opposite_direction": True,
                    },
                }

                sandwiches.append(sandwich)
                used_tx.add(frontrun["signature"])
                used_tx.add(victim["signature"])
                used_tx.add(back["signature"])

                break

    return sandwiches


def load_transactions(filepath=DEFAULT_TRANSACTIONS_FILE) -> List[Dict[str, Any]]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Transactions file not found: {filepath}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("transactions", [])


def save_sandwich_results(
    sandwiches: List[Dict[str, Any]],
    output_file: str = DEFAULT_OUTPUT_FILE,
) -> None:
    bot_wallets = set(s["attack_metadata"]["bot_wallet"] for s in sandwiches)
    victim_wallets = set(s["attack_metadata"]["victim_wallet"] for s in sandwiches)

    output_data = {
        "detection_timestamp": datetime.now().isoformat(),
        "total_sandwiches": len(sandwiches),
        "summary": {
            "unique_bot_wallets": len(bot_wallets),
            "unique_victim_wallets": len(victim_wallets),
        },
        "sandwiches": sandwiches,
    }

    output_path = Path(output_file)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, default=str)

    print(f"\nSandwich detection results saved to: {output_path.absolute()}")
    print(f"Total sandwiches detected: {len(sandwiches)}")
    print(f"Unique bot wallets: {output_data['summary']['unique_bot_wallets']}")


def run_detection(
    transactions_file=DEFAULT_TRANSACTIONS_FILE,
    output_file=DEFAULT_OUTPUT_FILE,
    max_slot_gap: int = MAX_SLOT_GAP,
    min_slot_gap: int = MIN_SLOT_GAP,
) -> None:

    print("=" * 70)
    print("WIDE SANDWICH ATTACK DETECTION")
    print("=" * 70)

    print(f"\nLoading transactions from: {transactions_file}")
    transactions = load_transactions(transactions_file)
    print(f"Loaded {len(transactions)} transactions")

    print(f"\nDetecting wide sandwich attacks...")
    print(f"  Max slot gap: {max_slot_gap}")
    print(f"  Min slot gap: {min_slot_gap}")

    sandwiches = detect_sandwiches(
        transactions,
    )

    print(f"Found {len(sandwiches)} potential sandwich attacks")

    print(f"\nDetecting bundle back-run patterns...")
    save_sandwich_results(sandwiches, output_file)

    print("\n" + "=" * 70)
    print("Detection complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import sys

    transactions_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TRANSACTIONS_FILE
    output_file = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_FILE

    run_detection(transactions_file, output_file)
