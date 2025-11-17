import asyncio
from typing import Optional, Dict, List, Any

from config import RAYDIUM_PROGRAM_ID, ORCA_PROGRAM_ID, RAYDIUM_CLMM_PROGRAM_ID


MINIMUM_BALANCE_CHANGE = 0.0001

BLOCK_REQUEST_DELAY_SECONDS = 0.05

KNOWN_DEX_PROGRAMS = {
    RAYDIUM_PROGRAM_ID: "Raydium CLMM",
    RAYDIUM_CLMM_PROGRAM_ID: "Raydium CLMM",
    ORCA_PROGRAM_ID: "Orca Whirlpools",
}


def identify_dex_program(transaction) -> tuple[bool, Optional[str]]:
    try:
        instructions = transaction.transaction.message.instructions

        for instruction in instructions:
            if not hasattr(instruction, "program_id"):
                continue

            program_id = str(instruction.program_id)

            if program_id in KNOWN_DEX_PROGRAMS:
                return True, KNOWN_DEX_PROGRAMS[program_id]

        return False, None

    except Exception:
        return False, None


def extract_transaction_signer(transaction) -> Optional[str]:
    try:
        account_keys = transaction.transaction.message.account_keys

        if not account_keys or len(account_keys) == 0:
            return None

        first_account = account_keys[0]

        if hasattr(first_account, "pubkey"):
            return str(first_account.pubkey)

        return str(first_account)

    except Exception:
        return None


def calculate_token_balance_changes(
    transaction, signer_address: str
) -> Optional[Dict[str, Any]]:
    try:
        transaction_metadata = transaction.meta

        # Track balance changes for each token mint
        token_balance_map = {}

        # Record pre-transaction balances and account info
        if hasattr(transaction_metadata, "pre_token_balances"):
            for balance_record in transaction_metadata.pre_token_balances:
                if not (
                    hasattr(balance_record, "mint")
                    and hasattr(balance_record, "ui_token_amount")
                ):
                    continue

                mint_address = str(balance_record.mint)
                balance_amount = balance_record.ui_token_amount.ui_amount or 0
                owner = (
                    str(balance_record.owner)
                    if hasattr(balance_record, "owner")
                    else None
                )

                token_balance_map[mint_address] = {
                    "before": balance_amount,
                    "after": 0,
                    "owner": owner,
                    "account": None,
                }

        # Record post-transaction balances and account info
        if hasattr(transaction_metadata, "post_token_balances"):
            for balance_record in transaction_metadata.post_token_balances:
                if not (
                    hasattr(balance_record, "mint")
                    and hasattr(balance_record, "ui_token_amount")
                ):
                    continue

                mint_address = str(balance_record.mint)
                balance_amount = balance_record.ui_token_amount.ui_amount or 0
                owner = (
                    str(balance_record.owner)
                    if hasattr(balance_record, "owner")
                    else None
                )

                if mint_address in token_balance_map:
                    token_balance_map[mint_address]["after"] = balance_amount
                    if owner:
                        token_balance_map[mint_address]["owner"] = owner
                else:
                    token_balance_map[mint_address] = {
                        "before": 0,
                        "after": balance_amount,
                        "owner": owner,
                        "account": None,
                    }

        # Also store account addresses from metadata
        account_keys = []
        try:
            message = transaction.transaction.message
            if hasattr(message, "account_keys"):
                account_keys = [
                    str(key.pubkey) if hasattr(key, "pubkey") else str(key)
                    for key in message.account_keys
                ]
        except Exception:
            pass

        # Map account indices to addresses for token accounts
        for balance_list in [
            getattr(transaction_metadata, "pre_token_balances", []),
            getattr(transaction_metadata, "post_token_balances", []),
        ]:
            for balance_record in balance_list:
                if hasattr(balance_record, "account_index") and hasattr(
                    balance_record, "mint"
                ):
                    account_index = balance_record.account_index
                    mint_address = str(balance_record.mint)
                    if mint_address in token_balance_map and account_index < len(
                        account_keys
                    ):
                        token_balance_map[mint_address]["account"] = account_keys[
                            account_index
                        ]

        # Identify tokens and amounts involved in the swap
        token_sent = None
        token_received = None
        amount_sent = 0
        amount_received = 0
        source_ata = None
        destination_ata = None

        for mint_address, balances in token_balance_map.items():
            balance_change = balances["after"] - balances["before"]
            owner = balances.get("owner")
            account = balances.get("account")

            # Only consider balances owned by the signer
            if owner and owner == signer_address:
                if balance_change < -MINIMUM_BALANCE_CHANGE:
                    # Negative change means token was sent out
                    token_sent = mint_address
                    amount_sent = abs(balance_change)
                    source_ata = account

                elif balance_change > MINIMUM_BALANCE_CHANGE:
                    # Positive change means token was received
                    token_received = mint_address
                    amount_received = balance_change
                    destination_ata = account

        # Only return if we have a complete swap (both sides)
        if token_sent and token_received:
            return {
                "token_in": token_sent,
                "token_out": token_received,
                "amount_in": amount_sent,
                "amount_out": amount_received,
                "user_source_ata": source_ata,
                "user_destination_ata": destination_ata,
            }

        return None

    except Exception:
        return None


def extract_swap_transaction_data(
    transaction, slot_number: int, program_to_pool_mapping: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    # Check if this is a DEX transaction
    is_dex_transaction, detected_dex_name = identify_dex_program(transaction)

    if not is_dex_transaction:
        return None

    # Extract key transaction details
    signer_address = extract_transaction_signer(transaction)

    if not signer_address:
        return None

    swap_details = calculate_token_balance_changes(transaction, signer_address)

    if not swap_details:
        return None

    # Try to match transaction to a specific configured pool
    pool_name = detected_dex_name  # Default to detected DEX name

    try:
        instructions = transaction.transaction.message.instructions
        for instruction in instructions:
            if hasattr(instruction, "program_id"):
                program_id = str(instruction.program_id)
                if program_id in program_to_pool_mapping:
                    pool_name = program_to_pool_mapping[program_id]
                    break
    except Exception:
        pass

    # Extract transaction signature
    try:
        transaction_signature = str(transaction.transaction.signatures[0])
    except Exception:
        transaction_signature = "unknown"

    return {
        "signature": transaction_signature,
        "slot": slot_number,
        "signer": signer_address,
        "pool_name": pool_name,
        "token_in": swap_details["token_in"],
        "amount_in": swap_details["amount_in"],
        "user_source_ata": swap_details["user_source_ata"],
        "token_out": swap_details["token_out"],
        "amount_out": swap_details["amount_out"],
        "user_destination_ata": swap_details["user_destination_ata"],
    }


async def process_single_block(
    rpc_client, slot_number: int, program_to_pool_mapping: Dict[str, str]
) -> List[Dict[str, Any]]:
    block_response = await rpc_client.get_block(
        slot_number, encoding="jsonParsed", max_supported_transaction_version=0
    )

    if not block_response.value:
        return []

    block_data = block_response.value
    discovered_swaps = []

    for transaction in block_data.transactions:
        swap_data = extract_swap_transaction_data(
            transaction, slot_number, program_to_pool_mapping
        )

        if swap_data:
            discovered_swaps.append(swap_data)

    return discovered_swaps


async def parse_blocks_for_txns(
    rpc_client, pool_configurations: List[Dict[str, str]], slot_window: int = 50
) -> List[Dict[str, Any]]:

    current_slot_response = await rpc_client.get_slot()
    current_slot = current_slot_response.value

    print(f"\nScanning {slot_window} recent slots starting from slot {current_slot}")

    program_to_pool_mapping = {
        pool["address"]: pool["name"] for pool in pool_configurations
    }

    all_discovered_transactions = []
    blocks_successfully_processed = 0

    for slot_offset in range(slot_window):
        target_slot = current_slot - slot_offset

        try:
            block_transactions = await process_single_block(
                rpc_client, target_slot, program_to_pool_mapping
            )

            all_discovered_transactions.extend(block_transactions)
            blocks_successfully_processed += 1

            await asyncio.sleep(BLOCK_REQUEST_DELAY_SECONDS)

        except Exception:
            # Skip blocks that fail to load or process
            continue

    print(f"Successfully processed {blocks_successfully_processed} blocks")
    print(f"Found {len(all_discovered_transactions)} swap transactions\n")

    return all_discovered_transactions
