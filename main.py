import asyncio
import json
from datetime import datetime

import config
from solana.rpc.async_api import AsyncClient

import utils


async def main():
    rpc_url = config.RPC_ENDPOINT
    if not rpc_url:
        print("ERROR: RPC URL is missing in the .env file")
        return

    async with AsyncClient(rpc_url) as client:
        res = await client.is_connected()
        print(f"Connected to RPC: {res}")

        # Pools to fetch txns from
        pools = [
            {
                "address": config.RAYDIUM_CLMM_PROGRAM_ID,
                "name": "Raydium CLMM",
            },
            {
                "address": config.ORCA_PROGRAM_ID,
                "name": "Orca Whirlpools",
            },
        ]

        print(f"Starting parallel fetch for {len(pools)} pools...")
        for pool in pools:
            print(f"- {pool['name']}")
        print()

        tasks = [
            utils.fetch_and_process_pool(
                client, pool["address"], pool["name"], limit=10
            )
            for pool in pools
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        print(f"\n{'='*60}")
        print(f"Saving Results")
        print(f"{'='*60}")

        for i, (pool, result) in enumerate(zip(pools, results)):
            if isinstance(result, Exception):
                print(f"\nError processing {pool['name']}: {result}")
                continue

            signatures_data, transactions_data = result

            if not signatures_data:
                print(f"\nNo data for {pool['name']}")
                continue

            # Save signatures
            sig_filename = f"signatures_{pool['address'][:8]}_{timestamp}.json"
            signatures_output = {
                "pool_address": pool["address"],
                "pool_name": pool["name"],
                "fetched_at": datetime.now().isoformat(),
                "total_signatures": len(signatures_data),
                "successful_signatures": len(signatures_data),
                "signatures": signatures_data,
            }

            with open(sig_filename, "w") as f:
                json.dump(signatures_output, f, indent=2, default=str)

            print(f"\n{pool['name']}:")
            print(f" Signatures: {len(signatures_data)} saved to {sig_filename}")

            # Save transactions
            if transactions_data:
                tx_filename = f"transactions_{pool['address'][:8]}_{timestamp}.json"
                transactions_output = {
                    "pool_address": pool["address"],
                    "pool_name": pool["name"],
                    "fetched_at": datetime.now().isoformat(),
                    "total_transactions": len(transactions_data),
                    "transactions": transactions_data,
                }

                with open(tx_filename, "w") as f:
                    json.dump(transactions_output, f, indent=2, default=str)

                print(f" Transactions: {len(transactions_data)} saved to {tx_filename}")

                # Print summary stats
                dex_transactions = [tx for tx in transactions_data if tx.get("dex")]
                print(f"   DEX transactions: {len(dex_transactions)}")
                if dex_transactions:
                    raydium_count = len(
                        [tx for tx in dex_transactions if tx.get("dex") == "Raydium"]
                    )
                    orca_count = len(
                        [tx for tx in dex_transactions if tx.get("dex") == "Orca"]
                    )
                    print(f" - Raydium: {raydium_count}")
                    print(f" - Orca: {orca_count}")

        print(f"\n{'='*60}")
        print(f"All done!")
        print(f"{'='*60}")


try:
    asyncio.run(main())
except Exception as e:
    print(f"ERROR: {e}")
