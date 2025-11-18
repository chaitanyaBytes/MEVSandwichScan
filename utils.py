import asyncio
from typing import Optional, Dict, List, Any

from config import (
    RAYDIUM_PROGRAM_ID,
    ORCA_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    JUPITER_V6_PROGRAM_ID,
    JUPITER_V4_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID,
)


MINIMUM_BALANCE_CHANGE = 0.0001

BLOCK_REQUEST_DELAY_SECONDS = 0.05

KNOWN_DEX_PROGRAMS = {
    RAYDIUM_PROGRAM_ID: "Raydium AMM",
    RAYDIUM_CLMM_PROGRAM_ID: "Raydium CLMM",
    ORCA_PROGRAM_ID: "Orca Whirlpools",
}

ALL_SWAP_PROGRAMS = KNOWN_DEX_PROGRAMS


def is_swap_by_logs(log_messages: List[str]) -> bool:
    if not log_messages:
        return False

    swap_log_patterns = [
        "Instruction: Swap",
        "Instruction: SwapV2",
        "Instruction: SwapBaseIn",
    ]

    for log in log_messages:
        if any(pattern in log for pattern in swap_log_patterns):
            return True

    return False


def identify_dex_program(transaction) -> tuple[bool, Optional[str]]:
    try:
        meta = transaction.meta
        message = transaction.transaction.message

        log_messages = getattr(meta, "log_messages", []) or []
        if is_swap_by_logs(log_messages):
            instructions = message.instructions
            for instruction in instructions:
                if not hasattr(instruction, "program_id"):
                    continue
                program_id = str(instruction.program_id)
                if program_id in ALL_SWAP_PROGRAMS:
                    return True, ALL_SWAP_PROGRAMS[program_id]

            inner_instructions = getattr(meta, "inner_instructions", []) or []
            for ix_group in inner_instructions:
                if hasattr(ix_group, "instructions"):
                    for ix in ix_group.instructions:
                        if hasattr(ix, "program_id"):
                            program_id = str(ix.program_id)
                            if program_id in ALL_SWAP_PROGRAMS:
                                return True, ALL_SWAP_PROGRAMS[program_id]

        instructions = message.instructions
        for instruction in instructions:
            if not hasattr(instruction, "program_id"):
                continue
            program_id = str(instruction.program_id)
            if program_id in ALL_SWAP_PROGRAMS:
                return True, ALL_SWAP_PROGRAMS[program_id]

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


def get_first_writable_account(transaction) -> Optional[str]:
    try:
        message = transaction.transaction.message
        account_keys = message.account_keys

        if not account_keys or len(account_keys) < 2:
            return None

        if hasattr(message, "header"):
            num_required_signatures = message.header.num_required_signatures
            if num_required_signatures < len(account_keys):
                first_writable = account_keys[num_required_signatures]
                if hasattr(first_writable, "pubkey"):
                    return str(first_writable.pubkey)
                return str(first_writable)

        second_account = account_keys[1]
        if hasattr(second_account, "pubkey"):
            return str(second_account.pubkey)
        return str(second_account)
    except Exception:
        return None


def calculate_token_balance_changes(
    transaction, signer_address: str
) -> Optional[Dict[str, Any]]:
    try:
        transaction_metadata = transaction.meta
        first_writable = get_first_writable_account(transaction)

        token_balance_map = {}

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

        relevant_changes = []

        for mint_address, balances in token_balance_map.items():
            balance_change = balances["after"] - balances["before"]
            owner = balances.get("owner")
            account = balances.get("account")

            is_relevant = True
            if owner:
                if owner == signer_address:
                    is_relevant = True
            elif first_writable and owner == first_writable:
                is_relevant = True

            if is_relevant and abs(balance_change) > MINIMUM_BALANCE_CHANGE:
                relevant_changes.append(
                    {
                        "mint": mint_address,
                        "change": balance_change,
                        "account": account,
                    }
                )

        relevant_changes.sort(key=lambda x: x["change"])

        token_sent = None
        token_received = None
        amount_sent = 0
        amount_received = 0
        source_ata = None
        destination_ata = None

        for change_info in relevant_changes:
            if change_info["change"] < -MINIMUM_BALANCE_CHANGE:
                token_sent = change_info["mint"]
                amount_sent = abs(change_info["change"])
                source_ata = change_info["account"]
                break

        for change_info in reversed(relevant_changes):
            if change_info["change"] > MINIMUM_BALANCE_CHANGE:
                token_received = change_info["mint"]
                amount_received = change_info["change"]
                destination_ata = change_info["account"]
                break

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


def extract_priority_fee_and_tip(transaction) -> Dict[str, Any]:
    """
    Extract priority fee (compute unit price) and tip account information.
    Returns: {priority_fee, tip_account, tip_amount}
    """
    priority_fee = None
    tip_account = None
    tip_amount = 0

    try:
        meta = transaction.meta
        message = transaction.transaction.message

        instructions = message.instructions
        for instruction in instructions:
            if hasattr(instruction, "program_id"):
                program_id = str(instruction.program_id)
                # Compute Budget Program ID
                if program_id == "ComputeBudget111111111111111111111111111111":
                    if hasattr(instruction, "data"):

                        pass

        pre_balances = getattr(meta, "pre_balances", []) or []
        post_balances = getattr(meta, "post_balances", []) or []
        account_keys = message.account_keys

        if pre_balances and post_balances and len(pre_balances) == len(post_balances):
            if len(pre_balances) > 0 and len(post_balances) > 0:
                signer_balance_change = post_balances[0] - pre_balances[0]
                if signer_balance_change < 0:
                    priority_fee = abs(signer_balance_change)

            for i in range(1, min(len(pre_balances), len(post_balances))):
                balance_change = post_balances[i] - pre_balances[i]
                if 1 <= balance_change <= 1000000:  # 0.001 SOL max tip
                    tip_amount = balance_change
                    if i < len(account_keys):
                        account = account_keys[i]
                        if hasattr(account, "pubkey"):
                            tip_account = str(account.pubkey)
                        else:
                            tip_account = str(account)
                        break

    except Exception:
        pass

    return {
        "priority_fee": priority_fee,
        "tip_account": tip_account,
        "tip_amount": tip_amount,
    }


def extract_swap_transaction_data(
    transaction,
    slot_number: int,
    tx_index: int,
    program_to_pool_mapping: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    is_dex_transaction, detected_dex_name = identify_dex_program(transaction)

    if not is_dex_transaction:
        return None

    signer_address = extract_transaction_signer(transaction)

    if not signer_address:
        return None

    swap_details = calculate_token_balance_changes(transaction, signer_address)

    if not swap_details:
        return None

    pool_name = detected_dex_name

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

    try:
        transaction_signature = str(transaction.transaction.signatures[0])
    except Exception:
        transaction_signature = "unknown"

    fee_info = extract_priority_fee_and_tip(transaction)

    return {
        "signature": transaction_signature,
        "slot": slot_number,
        "tx_index": tx_index,
        "signer": signer_address,
        "swap_program": detected_dex_name,
        "pool_name": pool_name,
        "token_in": swap_details["token_in"],
        "token_out": swap_details["token_out"],
        "amount_in": swap_details["amount_in"],
        "amount_out": swap_details["amount_out"],
        "user_source_ata": swap_details["user_source_ata"],
        "user_destination_ata": swap_details["user_destination_ata"],
        "priority_fee": fee_info["priority_fee"],
        "tip_account": fee_info["tip_account"],
        "tip_amount": fee_info["tip_amount"],
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

    transactions = getattr(block_data, "transactions", []) or []
    for tx_index, transaction in enumerate(transactions):
        swap_data = extract_swap_transaction_data(
            transaction, slot_number, tx_index, program_to_pool_mapping
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

    for target_slot in range(current_slot, current_slot - slot_window, -1):

        try:
            block_transactions = await process_single_block(
                rpc_client, target_slot, program_to_pool_mapping
            )

            all_discovered_transactions.extend(block_transactions)
            blocks_successfully_processed += 1

            await asyncio.sleep(BLOCK_REQUEST_DELAY_SECONDS)

        except Exception:
            continue

    print(f"Successfully processed {blocks_successfully_processed} blocks")
    print(f"Found {len(all_discovered_transactions)} swap transactions\n")

    return all_discovered_transactions
