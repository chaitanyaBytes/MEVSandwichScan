# Solana MEV Sandwich Attack Detection

A Python tool for scanning Solana blockchain blocks, detecting wide sandwich attacks, analyzing profits, and simulating attack scenarios on DEX pools.

## Features

- Scans recent Solana blocks for DEX swap transactions
- Supports multiple DEX pools: Raydium AMM, Raydium CLMM, Orca Whirlpools, Jupiter V6, Meteora DLMM
- Detects wide sandwich attacks across multiple slots
- Calculates profit/loss in USD and SOL for detected attacks
- Simulates sandwich attack scenarios with AMM math
- Fetches real-time token prices from Jupiter API
- Organizes all outputs in a results directory

## Project Structure

```
MEVSandwichScan/
├── main.py              # Main entry point - orchestrates scanning, detection, and analysis
├── utils.py             # Blockchain scanning and transaction parsing utilities
├── config.py            # Configuration and constants (RPC endpoints, program IDs)
├── sandwich_detect.py   # Wide sandwich attack detection logic
├── profit_analysis.py   # Profit calculation and PnL reporting
├── price_fetcher.py     # Token price fetching from Jupiter API
├── simulation.py        # Sandwich attack simulation with AMM math
├── results/             # All output files (created automatically)
│   ├── transactions.json
│   ├── sandwich_attacks.json
│   ├── profit_analysis.json
│   ├── pnl_report_per_bot.json
│   └── simulation.json
└── requiremnts.txt     # Python dependencies
```

## Installation

1. **Set up virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

2. **Install dependencies**

   ```bash
   pip install -r requiremnts.txt
   ```

   Or manually:

   ```bash
   pip install solana solders python-dotenv requests
   ```

3. **Configure environment**

   Create a `.env` file with your Solana RPC endpoint:

   ```
   RPC_ENDPOINT=https://api.mainnet-beta.solana.com
   ```

   Or use a service like Helius:

   ```
   RPC_ENDPOINT=https://mainnet.helius-rpc.com/?api-key=YOUR_API_KEY
   ```

## Usage

### Full Pipeline

Run the complete pipeline (scan, detect, analyze):

```bash
python main.py
```

This will:

1. Scan recent Solana blocks for DEX transactions
2. Detect wide sandwich attacks
3. Calculate profits in USD and SOL
4. Save all results to the `results/` directory

### Individual Components

**Run Sandwich Detection Only**

```bash
python sandwich_detect.py [transactions_file] [output_file]
```

**Run Profit Analysis**

```bash
python profit_analysis.py
```

This reads `results/sandwich_attacks.json` and generates:

- `results/profit_analysis.json` - Detailed per-sandwich analysis
- `results/pnl_report_per_bot.json` - Aggregated bot-level PnL

**Run Simulation**

```bash
python simulation.py
```

Generates a simulated sandwich attack scenario and saves to `results/simulation.json`.

## Core Modules

### main.py

Main orchestration script that:

- Scans blockchain blocks for DEX transactions
- Runs sandwich detection on discovered transactions
- Performs profit analysis on detected attacks
- Saves all outputs to `results/` directory

Key functions:

- `run_blockchain_scanner()` - Main scanning orchestration
- `get_monitored_pools()` - Returns list of DEX pools to monitor
- `save_transactions_to_file()` - Saves transaction data

### utils.py

Blockchain interaction and transaction parsing:

- `parse_blocks_for_txns()` - Scans blocks and extracts swap transactions
- `process_single_block()` - Processes individual blocks
- `extract_swap_transaction_data()` - Extracts swap details from transactions
- `calculate_token_balance_changes()` - Analyzes token balance changes
- `identify_dex_program()` - Identifies which DEX program executed the swap

### sandwich_detect.py

Wide sandwich attack detection:

- `detect_sandwiches()` - Main detection algorithm
- `is_opposite_direction()` - Checks if transactions are opposite directions
- `is_same_direction()` - Checks if transactions are same direction
- `load_transactions()` - Loads transaction data from JSON
- `run_detection()` - Orchestrates detection process

Detects sandwich patterns where:

- Front-run transaction occurs before victim
- Victim transaction in between
- Back-run transaction occurs after victim
- All within configurable slot gaps (default: 1-10 slots)

### profit_analysis.py

Profit calculation and reporting:

- `compute_profit()` - Calculates profit for each sandwich
- `summarize_results()` - Aggregates statistics
- `print_summary()` - Displays formatted summary
- `run_profit_analysis()` - Main analysis pipeline

Features:

- Fetches token prices from Jupiter API
- Calculates profit in both token units and USD/SOL
- Groups results by bot wallet
- Identifies most profitable attacks

### price_fetcher.py

Token price fetching:

- `fetch_prices_usd()` - Fetches USD prices from Jupiter lite API
- Handles batching for multiple tokens
- Gracefully handles API failures

### simulation.py

Sandwich attack simulation:

- `PoolState` - AMM pool state management (constant product formula)
- `run_simulation()` - Simulates a complete sandwich attack
- `print_simulation_summary()` - Displays simulation results
- Models front-run, victim, and back-run transactions

## Output Files

All outputs are saved in the `results/` directory:

### results/transactions.json

Raw transaction data from blockchain scan:

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
      "token_in": "So11111111111111111111111111111111111111112",
      "amount_in": 1.5,
      "token_out": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "amount_out": 150.0
    }
  ]
}
```

### results/sandwich_attacks.json

Detected sandwich attacks with metadata:

```json
{
  "detection_timestamp": "2025-11-17T22:35:10.123456",
  "total_sandwiches": 5,
  "summary": {
    "unique_bot_wallets": 3,
    "unique_victim_wallets": 5
  },
  "sandwiches": [
    {
      "front_run": { ... },
      "victim": { ... },
      "back_run": { ... },
      "attack_metadata": {
        "slot_gap_front_to_victim": 1,
        "slot_gap_victim_to_backrun": 3,
        "bot_wallet": "...",
        "victim_wallet": "..."
      }
    }
  ]
}
```

### results/profit_analysis.json

Detailed profit analysis for each sandwich:

```json
{
  "summary": {
    "total_sandwiches": 5,
    "profitable_count": 3,
    "total_profit_usd": 1250.50,
    "total_profit_sol": 8.75
  },
  "records": [
    {
      "sandwich_id": 1,
      "bot": "...",
      "profit_usd": 450.25,
      "profit_sol": 3.15,
      "token_spent": "...",
      "token_received": "..."
    }
  ]
}
```

### results/pnl_report_per_bot.json

Aggregated PnL by bot wallet:

```json
{
  "bot_address": {
    "sandwich_count": 5,
    "profit_usd": 1250.50,
    "profit_sol": 8.75
  }
}
```

### results/simulation.json

Simulated sandwich attack transactions:

```json
{
  "transactions": [
    {
      "signature": "SIM_FRONT",
      "slot": 10000,
      "signer": "BOT_WALLET_ABC",
      "token_in": "So11111111111111111111111111111111111111112",
      "amount_in": 20.0,
      "token_out": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "amount_out": 39215.6073
    }
  ]
}
```

## Configuration

### Adjustable Constants

**main.py:**

- `DEFAULT_SLOT_WINDOW` - Number of slots to scan (default: 300)

**sandwich_detect.py:**

- `MAX_SLOT_GAP` - Maximum slots between front-run and back-run (default: 10)
- `MIN_SLOT_GAP` - Minimum slots between front-run and victim (default: 1)

**utils.py:**

- `MINIMUM_BALANCE_CHANGE` - Threshold for detecting balance changes (default: 0.0001)
- `BLOCK_REQUEST_DELAY_SECONDS` - Delay between block requests (default: 0.05)

**price_fetcher.py:**

- `BATCH_SIZE` - Number of tokens to fetch per API call (default: 50)

### Adding New DEX Pools

1. Add program ID to `config.py`:

```python
YOUR_PROGRAM_ID = "YourProgramIdHere..."
```

2. Update `utils.py` to recognize the program:

```python
KNOWN_DEX_PROGRAMS = {
    ...
    YOUR_PROGRAM_ID: "Your DEX Name",
}
```

3. Add to `main.py` in `get_monitored_pools()`:

```python
{
    "address": config.YOUR_PROGRAM_ID,
    "name": "Your DEX Name",
}
```

## Example Output

```
======================================================================
SOLANA DEX TRANSACTION SCANNER
======================================================================
Connected to RPC: https://mainnet.helius-rpc.com/?api-key=b5d163ff-c323-4ed3-9a20-62cefe3fcf7f
Monitoring 5 DEX pools:
  - Raydium AMM
  - Raydium CLMM
  - Orca Whirlpools
  - Jupiter V6
  - Meteora DLMM
Scanning 300 recent slots starting from slot 380951822
Successfully processed 300 blocks
Found 3244 swap transactions
======================================================================
SCAN RESULTS
======================================================================
Total transactions found: 3244
Breakdown by pool:
  - Raydium AMM: 195 transactions (6.0%)
  - Raydium CLMM: 2057 transactions (63.4%)
  - Orca Whirlpools: 286 transactions (8.8%)
  - Jupiter V6: 705 transactions (21.7%)
  - Meteora DLMM: 1 transactions (0.0%)
Results saved to: results/transactions.json
======================================================================
Running Wide Sandwich Detection
======================================================================
======================================================================
WIDE SANDWICH ATTACK DETECTION
======================================================================
Loading transactions from: results/transactions.json
Loaded 3244 transactions
Detecting wide sandwich attacks...
  Max slot gap: 10
  Min slot gap: 1
Found 359 potential sandwich attacks
Detecting bundle back-run patterns...
Sandwich detection results saved to: results/sandwich_attacks.json
Total sandwiches detected: 359
Unique bot wallets: 76
======================================================================
Detection complete
======================================================================
======================================================================
Running SOL Profit Analysis
======================================================================
======================================================================
PROFIT ANALYSIS
======================================================================
 Loading sandwiches from: results/sandwich_attacks.json
 Loaded 359 sandwiches

 Fetching token prices from Jupiter...
 Fetched 11 token prices
   SOL price: $141.08 USD
 Computing profits for each sandwich...
 Processed 359 sandwiches successfully
======================================================================
PROFIT ANALYSIS SUMMARY
======================================================================
 OVERVIEW
----------------------------------------------------------------------
  Total Sandwiches Analyzed: 359
   Profitable: 133 (37.0%)
   Losing:     226
 PROFIT METRICS
----------------------------------------------------------------------
  Total Profit:     $-75,703.99 USD
                    -536.596183 SOL
  Best Sandwich:    $3,497.30 USD
                    24.789139 SOL
 TOP BOTS BY PROFIT
----------------------------------------------------------------------
  #1 Gwwnuytsvw7DC1Wea2QF...
     Profit: $8,633.66 USD (61.196077 SOL)
     Sandwiches: 28
  #2 ATQs6A92eUzdxTBsQhRJ...
     Profit: $566.37 USD (4.014497 SOL)
     Sandwiches: 3
  #3 BijofPtrG5AAvmb74KqW...
     Profit: $280.10 USD (1.985350 SOL)
     Sandwiches: 3
  #4 FrSbj9hGbMB6BLM6XMvR...
     Profit: $178.70 USD (1.266631 SOL)
     Sandwiches: 2
  #5 EQGEmqCuobe4MyVn7DfC...
     Profit: $129.86 USD (0.920431 SOL)
     Sandwiches: 2
======================================================================
 Saving results...
  Saved: profit_analysis.json
  Saved: pnl_report_per_bot.json
 Analysis complete!
======================================================================
Scan complete
======================================================================
```

## Wide Sandwich Attacks

This tool specifically detects "wide sandwich attacks" where:

1. **Front-run**: Bot transaction executes in slot N, moving price unfavorably for the victim
2. **Victim**: User transaction executes in slot N+1 to N+2, getting worse execution
3. **Back-run**: Bot transaction executes in slot N+3 or later, profiting from the price movement

The "wide" aspect refers to the multi-slot gap between front-run and back-run, which helps bots evade single-slot detection systems.

## Simulation

The simulation module demonstrates how sandwich attacks work:

- Models a constant-product AMM (x * y = k)
- Simulates bot front-run, victim trade, and bot back-run
- Calculates price impact and profit/loss
- Shows timing across multiple slots
- Generates transaction objects compatible with the detector

## Notes

- Only complete swaps are included (both token_in and token_out must be present)
- Failed or partial transactions are automatically filtered out
- The scanner works backward from the most recent slot
- Rate limiting is built in to avoid overwhelming RPC endpoints
- Price fetching requires internet connection to Jupiter API
- All JSON outputs are automatically saved to the `results/` directory
- The `results/` directory is created automatically if it doesn't exist

## License

MIT
