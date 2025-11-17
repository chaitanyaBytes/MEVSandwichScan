import asyncio
from datetime import datetime
from solders.signature import Signature
from solders.pubkey import Pubkey


def extract_transaction_data(pool_name, transaction, signature_str):
    try:
        tx_data = {
            "pool_name": pool_name,
            "signature": str(signature_str),
            "slot": transaction.slot if hasattr(transaction, "slot") else None,
            "block_time": (
                transaction.block_time if hasattr(transaction, "block_time") else None
            ),
            "fee": (
                transaction.transaction.meta.fee
                if transaction.transaction.meta.fee
                else 0
            ),
        }
        tx_data["signer_address"] = get_signer_address(transaction)

        if tx_data["block_time"]:
            tx_data["block_time_readable"] = datetime.fromtimestamp(
                tx_data["block_time"]
            ).strftime("%Y-%m-%d %H:%M:%S UTC")

        return tx_data
    except Exception as e:
        return None


async def fetch_transaction(client, pool_name, signature_str):
    try:
        sig = Signature.from_string(signature_str)
        tx_response = await client.get_transaction(
            sig,
            encoding="jsonParsed",
            max_supported_transaction_version=0,
        )

        if tx_response.value:
            return extract_transaction_data(pool_name, tx_response.value, signature_str)
        return None
    except Exception as e:
        return None


async def fetch_and_process_pool(client, pool_address, pool_name, limit=100):
    print(f"Fetching data for {pool_name} ({pool_address[:8]}...)\n")

    signature_res = await client.get_signatures_for_address(
        account=Pubkey.from_string(pool_address),
        limit=limit,
        commitment="finalized",
    )

    if not signature_res.value:
        print(f"No signatures found for {pool_name}")
        return None, []

    signatures_data = []

    for sig_info in signature_res.value:
        if sig_info.err is not None:
            continue

        sig_dict = {
            "signature": str(sig_info.signature) if sig_info.signature else None,
            "slot": sig_info.slot,
            "err": None,
            "memo": sig_info.memo if hasattr(sig_info, "memo") else None,
            "block_time": sig_info.block_time if sig_info.block_time else None,
            "confirmation_status": (
                str(sig_info.confirmation_status)
                if sig_info.confirmation_status
                else None
            ),
        }

        if sig_dict["block_time"]:
            sig_dict["block_time_readable"] = datetime.fromtimestamp(
                sig_dict["block_time"]
            ).strftime("%Y-%m-%d %H:%M:%S UTC")

        signatures_data.append(sig_dict)

    print(f"Found {len(signatures_data)} successful signatures in {pool_name}")

    tasks = [
        fetch_transaction(client, pool_name, sig_dict["signature"])
        for sig_dict in signatures_data
    ]

    transactions_data = []
    batch_size = 20

    for i in range(0, len(tasks), batch_size):
        batch = tasks[i : i + batch_size]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)

        for result in batch_results:
            if isinstance(result, Exception):
                continue
            if result:
                transactions_data.append(result)

        # Small delay between batches
        if i + batch_size < len(tasks):
            await asyncio.sleep(0.1)

        print(
            f"Progress: {min(i + batch_size, len(tasks))}/{len(tasks)} transactions fetched"
        )

    print(f"Successfully fetched {len(transactions_data)} transactions")

    return signatures_data, transactions_data


def get_signer_address(transaction):
    try:
        signer_address = None
        if (
            hasattr(transaction, "transaction")
            and hasattr(transaction.transaction, "transaction")
            and hasattr(transaction.transaction.transaction, "message")
        ):

            message = transaction.transaction.transaction.message
            account_keys = None
            if hasattr(message, "account_keys") and len(message.account_keys) > 0:
                account_keys = message.account_keys
            elif (
                hasattr(message, "static_account_keys")
                and len(message.static_account_keys) > 0
            ):
                account_keys = message.static_account_keys

            if account_keys:
                first_account = account_keys[0]
                if isinstance(first_account, str):
                    signer_address = first_account
                elif hasattr(first_account, "pubkey"):
                    signer_address = str(first_account.pubkey)
                elif isinstance(first_account, dict) and "pubkey" in first_account:
                    signer_address = str(first_account["pubkey"])
                else:
                    signer_address = str(first_account)
            return signer_address
    except Exception as e:
        return None
