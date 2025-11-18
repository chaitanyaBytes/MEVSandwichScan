"""
Solana DEX Transaction Scanner

Scans recent Solana blockchain blocks to identify and extract swap transactions
from configured DEX pools (Raydium and Orca).
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import config
from solana.rpc.async_api import AsyncClient
import sandwich_detect

import utils
import profit_analysis


OUTPUT_FILENAME = "transactions.json"
DEFAULT_SLOT_WINDOW = 300


def get_monitored_pools() -> List[Dict[str, str]]:
    return [
        {
            "address": config.RAYDIUM_PROGRAM_ID,
            "name": "Raydium AMM",
        },
        {
            "address": config.RAYDIUM_CLMM_PROGRAM_ID,
            "name": "Raydium CLMM",
        },
        {
            "address": config.ORCA_PROGRAM_ID,
            "name": "Orca Whirlpools",
        },
        {
            "address": config.JUPITER_V6_PROGRAM_ID,
            "name": "Jupiter V6",
        },
        {
            "address": config.METEORA_DLMM_PROGRAM_ID,
            "name": "Meteora DLMM",
        },
    ]


def calculate_pool_statistics(
    transactions: List[Dict[str, Any]], pool_configurations: List[Dict[str, str]]
) -> Dict[str, int]:
    pool_transaction_counts = {}

    for pool_config in pool_configurations:
        pool_name = pool_config["name"]
        transaction_count = sum(
            1 for tx in transactions if tx["pool_name"] == pool_name
        )
        pool_transaction_counts[pool_name] = transaction_count

    return pool_transaction_counts


def print_scan_results(
    transactions: List[Dict[str, Any]], pool_configurations: List[Dict[str, str]]
) -> None:
    print("\n" + "=" * 70)
    print("SCAN RESULTS")
    print("=" * 70)

    if not transactions:
        print("\nNo swap transactions found in the scanned blocks.")
        return

    pool_statistics = calculate_pool_statistics(transactions, pool_configurations)

    print(f"\nTotal transactions found: {len(transactions)}")
    print("\nBreakdown by pool:")

    for pool_name, count in pool_statistics.items():
        percentage = (count / len(transactions) * 100) if transactions else 0
        print(f"  - {pool_name}: {count} transactions ({percentage:.1f}%)")


def save_transactions_to_file(
    transactions: List[Dict[str, Any]], output_filepath: str = OUTPUT_FILENAME
) -> None:
    output_data = {
        "scan_timestamp": datetime.now().isoformat(),
        "total_count": len(transactions),
        "transactions": transactions,
    }

    output_path = Path(output_filepath)

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(output_data, output_file, indent=2, default=str)

    print(f"\nResults saved to: {output_path.absolute()}")


async def run_blockchain_scanner(slot_window: int = DEFAULT_SLOT_WINDOW) -> None:
    rpc_endpoint = config.RPC_ENDPOINT
    if not rpc_endpoint:
        print("ERROR: RPC_ENDPOINT not configured. Please check your .env file.")
        return

    print("=" * 70)
    print("SOLANA DEX TRANSACTION SCANNER")
    print("=" * 70)

    async with AsyncClient(rpc_endpoint) as rpc_client:
        is_connected = await rpc_client.is_connected()

        if not is_connected:
            print("ERROR: Failed to connect to Solana RPC endpoint")
            return

        print(f"\nConnected to RPC: {rpc_endpoint}")

        monitored_pools = get_monitored_pools()

        print(f"\nMonitoring {len(monitored_pools)} DEX pools:")
        for pool in monitored_pools:
            print(f"  - {pool['name']}")

        # Scan blockchain for swap transactions
        discovered_transactions = await utils.parse_blocks_for_txns(
            rpc_client, monitored_pools, slot_window=slot_window
        )

        print_scan_results(discovered_transactions, monitored_pools)

        if discovered_transactions:
            save_transactions_to_file(discovered_transactions)

            # Run sandwich detection
            print("\n" + "=" * 70)
            print("Running Wide Sandwich Detection")
            print("=" * 70)

            try:
                sandwich_detect.run_detection(
                    transactions_file=OUTPUT_FILENAME,
                    output_file="sandwich_attacks.json",
                )
            except Exception as e:
                print(f"Error during sandwich detection: {e}")
            else:
                print("\n" + "=" * 70)
                print("Running SOL Profit Analysis")
                print("=" * 70)
                try:
                    profit_analysis.run_profit_analysis(
                        Path("sandwich_attacks.json"),
                        Path("profit_analysis.json"),
                        Path("pnl_report_per_bot.json"),
                    )
                except Exception as e:
                    print(f"Error during profit analysis: {e}")

        print("\n" + "=" * 70)
        print("Scan complete")
        print("=" * 70 + "\n")


try:
    asyncio.run(run_blockchain_scanner())
except KeyboardInterrupt:
    print("\n\nScan interrupted by user")
except Exception as error:
    print(f"\nERROR: {error}")
    raise
