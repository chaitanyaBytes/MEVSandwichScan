# Solana DEX Transaction Scanner

A Python tool for scanning Solana blockchain blocks to identify and extract DEX swap transactions from Raydium and Orca pools.

## Features

- Scans recent Solana blocks for DEX transactions
- Supports Raydium CLMM and Orca Whirlpools
- Extracts detailed swap information including tokens and amounts
- Clean, functional code with descriptive naming
- Saves results in structured JSON format

## Project Structure

```
MEVSandwichScan/
├── main.py          # Application entry point and orchestration
├── utils.py         # Blockchain scanning and parsing utilities
├── config.py        # Configuration and constants
└── transactions.json # Output file with discovered swaps
```

## Core Functions

### utils.py

- `parse_blocks_for_txns()` - Main function to scan blocks and return transactions
- `process_single_block()` - Process a single block for swap transactions
- `extract_swap_transaction_data()` - Extract complete swap data from a transaction
- `calculate_token_balance_changes()` - Analyze token balance changes
- `identify_dex_program()` - Check if transaction involves a DEX
- `extract_transaction_signer()` - Get the transaction signer address

### main.py

- `run_blockchain_scanner()` - Main scanning orchestration
- `get_monitored_pools()` - Returns list of pools to monitor
- `print_scan_results()` - Display scan summary
- `calculate_pool_statistics()` - Calculate per-pool transaction counts
- `save_transactions_to_file()` - Save results to JSON

## Installation

1. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

2. **Install dependencies**
   ```bash
   pip install solana solders python-dotenv
   ```

3. **Configure environment**
   
   Create a `.env` file with your Solana RPC endpoint:
   ```
   RPC_ENDPOINT=https://api.mainnet-beta.solana.com
   ```

## Usage

### Basic Scan

Run the scanner with default settings (100 slots):

```bash
python main.py
```

### Custom Configuration

Modify `DEFAULT_SLOT_WINDOW` in `main.py` or adjust the function call:

```python
asyncio.run(run_blockchain_scanner(slot_window=200))
```

## Output Format

Results are saved to `transactions.json`:

```json
{
  "scan_timestamp": "2025-11-17T22:34:25.578444",
  "total_count": 52,
  "transactions": [
    {
      "signature": "54nsyoWgzfDJJ54F8UkVAA7Nqx6ALuyw354Fzr6qwN4H...",
      "slot": 380716048,
      "signer": "Gs5rez2psonpHZmSN1TRGw4u46htHt6iLDygNd78sXZr",
      "pool_name": "Raydium CLMM",
      "token_in": "3hfMw3RXu7wtHWebfJBdeNr5Ac9xEzLJ95x4Tk6uX3QA",
      "amount_in": 922.08,
      "user_source_ata": "7YttLkHDoNj9wyDur5pM1ejNaAvT9X4eqaYcHQqtj2G5",
      "token_out": "DNduJ3mBepTdrjtA6XGPyJ7UeK9BgXKyRnMCJgAobiYM",
      "amount_out": 5639.79,
      "user_destination_ata": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    }
  ]
}
```

### Field Descriptions

- `signature` - Unique transaction signature
- `slot` - Block slot number where transaction occurred
- `signer` - Transaction signer (fee payer) wallet address
- `pool_name` - DEX pool name (e.g., "Raydium CLMM", "Orca Whirlpools")
- `token_in` - Mint address of the token sent/sold
- `amount_in` - Amount of token sent (in UI units)
- `user_source_ata` - User's Associated Token Account for the source token
- `token_out` - Mint address of the token received/bought
- `amount_out` - Amount of token received (in UI units)
- `user_destination_ata` - User's Associated Token Account for the destination token

## Configuration

### Adding New DEX Pools

1. Add program ID to `utils.py`:

```python
KNOWN_DEX_PROGRAMS = {
    RAYDIUM_PROGRAM_ID: "Raydium CLMM",
    RAYDIUM_CLMM_PROGRAM_ID: "Raydium CLMM",
    ORCA_PROGRAM_ID: "Orca Whirlpools",
    YOUR_PROGRAM_ID: "Your DEX Name",  # Add here
}
```

2. Update `main.py` in `get_monitored_pools()`:

```python
{
    "address": config.YOUR_PROGRAM_ID,
    "name": "Your DEX Name",
}
```

### Adjustable Constants

In `utils.py`:

- `MINIMUM_BALANCE_CHANGE` - Threshold for detecting balance changes (default: 0.0001)
- `BLOCK_REQUEST_DELAY_SECONDS` - Delay between block requests (default: 0.05)

In `main.py`:

- `DEFAULT_SLOT_WINDOW` - Number of slots to scan (default: 100)
- `OUTPUT_FILENAME` - Output file name (default: "transactions.json")

## Example Output

```
======================================================================
SOLANA DEX TRANSACTION SCANNER
======================================================================

Connected to RPC: https://api.mainnet-beta.solana.com

Monitoring 2 DEX pools:
  - Raydium CLMM
  - Orca Whirlpools

Scanning 100 recent slots starting from slot 380716048
Successfully processed 100 blocks
Found 52 swap transactions

======================================================================
SCAN RESULTS
======================================================================

Total transactions found: 52

Breakdown by pool:
  - Raydium CLMM: 45 transactions (86.5%)
  - Orca Whirlpools: 7 transactions (13.5%)

Results saved to: /path/to/transactions.json

======================================================================
Scan complete
======================================================================
```

## Notes

- Only complete swaps are included (both token_in and token_out must be present)
- Failed or partial transactions are automatically filtered out
- The scanner works backward from the most recent slot
- Rate limiting is built in to avoid overwhelming RPC endpoints

## License

MIT
