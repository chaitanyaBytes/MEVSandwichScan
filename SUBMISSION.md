# MEV Sandwich Attack Detection on Solana: Research Submission

## Project Thread

This project developed a comprehensive system for detecting and analyzing wide sandwich attacks on Solana's decentralized exchange (DEX) ecosystem. The work began with building a blockchain scanner capable of extracting swap transactions from multiple DEX protocols (Raydium, Orca, Jupiter, Meteora) by parsing Solana blocks and analyzing token balance changes.

The core challenge was detecting "wide" sandwich attacks—MEV extraction strategies where bots place front-run and back-run transactions across multiple slots, making them harder to detect than single-slot attacks. Our detection algorithm identifies patterns where: (1) a bot transaction executes before a victim's swap, (2) the victim's transaction occurs in between, and (3) the bot executes a closing transaction in a later slot, all within configurable slot gaps (1-10 slots).

To validate detected attacks, we implemented a profit analysis system that fetches real-time token prices from Jupiter's API and calculates profitability in both token units and USD/SOL equivalents. The analysis revealed that only 37% of detected sandwich attempts are actually profitable, with many bots experiencing losses due to gas fees, price slippage, or failed execution timing.

The system includes a simulation module that models sandwich attacks using constant-product AMM mathematics, demonstrating how price impact affects both bot profits and victim losses. This simulation helps understand attack mechanics and validate detection logic.

All components are integrated into a unified pipeline that scans blocks, detects attacks, analyzes profits, and generates comprehensive reports. The system successfully processed 3,244 transactions from 300 recent slots, identifying 359 potential sandwich attacks across 76 unique bot wallets.

## Research Log

**Tools and Technologies Used:**

The project leverages Python 3 with the Solana Python SDK (`solana` and `solders` libraries) for blockchain interaction. I have used asynchronous RPC calls to fetch block data from Helius and other Solana RPC providers. Transaction parsing involves analyzing instruction data, account balance changes, and program IDs to identify DEX swaps across Raydium AMM/CLMM, Orca Whirlpools, Jupiter V6, and Meteora DLMM protocols.

For price data, I have integrated Jupiter's lite API (`lite-api.jup.ag/price/v3`) to fetch USD prices for tokens, enabling profit calculations. The system implements batching (50 tokens per request) and retry logic to handle API rate limits and network failures gracefully.

**Challenges Encountered:**

The main technical challenge was detecting cross-slot attack traces. Unlike Ethereum where transactions are atomic within a single block, Solana's slot-based architecture means sandwich attacks can span multiple slots, requiring careful slot gap analysis. I implemented a sliding window algorithm that tracks transaction sequences across slots while maintaining O(n²) complexity for pattern matching.

Another significant challenge was handling diverse token types and calculating profits in a token-agnostic manner. Initial implementations were SOL-specific, but I refactored to dynamically identify profit tokens and convert to USD using fetched prices. This required careful handling of edge cases where price data might be unavailable.

Parsing inner instructions presented additional complexity, as Solana transactions often contain nested instruction calls where the actual swap logic resides. DEX programs frequently delegate swap execution to inner instructions, requiring recursive traversal of the instruction tree to extract token amounts and identify the true swap parameters. This necessitated careful parsing of both top-level and nested instruction data structures.

Network reliability issues with price APIs necessitated defensive programming—implementing fallbacks, error handling, and graceful degradation when external services fail.

**Verification Steps:**

I verified detection accuracy through multiple methods: (1) Manual inspection of detected sandwich sequences, confirming front-run/victim/back-run patterns, (2) Cross-referencing bot wallet addresses across multiple detected attacks, (3) Validating profit calculations by comparing against on-chain balance changes, and (4) Running simulations with known parameters and verifying mathematical correctness of AMM calculations.

The system processes real mainnet data (3,244 transactions, 359 detected attacks) with results showing realistic patterns: 37% profitability rate, negative total profit indicating many failed attempts, and top-performing bots with consistent attack patterns.

**Future Hypotheses:**

As Solana's validator infrastructure evolves, particularly with Firedancer's implementation, I hypothesize that wide sandwich attacks may become less profitable. Firedancer's improved validator diversity and faster block production could reduce the predictability of transaction ordering across slots, making it harder for bots to reliably execute multi-slot strategies. Additionally, increased validator decentralization may reduce the effectiveness of timing-based MEV extraction, as transaction inclusion becomes less predictable. However, sophisticated bots may adapt by using more advanced techniques like bundle transactions or validator-specific strategies. The MEV landscape will likely shift toward more complex, harder-to-detect strategies as basic sandwich attacks become less viable.

Furthermore, the emerging privacy-focused protocols in the crypto ecosystem present another potential mitigation strategy. DEXs implementing private and encrypted swap mechanisms—where transaction details remain hidden until execution—could fundamentally prevent sandwich attacks by hiding the information bots need to identify profitable opportunities. Protocols that implement cryptographic techniques like zero-knowledge proofs or encrypted mempools may offer sustainable protection against MEV extraction, as bots cannot front-run transactions they cannot observe. This privacy-centric approach represents a paradigm shift from reactive detection to proactive prevention of MEV attacks and I am firm believer.
