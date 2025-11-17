import os
from dotenv import load_dotenv

load_dotenv()

RPC_ENDPOINT = os.getenv("MAINNET_RPC_URL", "https://api.mainnet-beta.solana.com")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", None)

if HELIUS_API_KEY:
    RPC_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"


ANALYSIS_WINDOW_SECONDS = 7 * 24 * 60 * 60

# DEX Program IDs
RAYDIUM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"  # Raydium AMM
RAYDIUM_CLMM_PROGRAM_ID = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"  # Raydium CLMM
ORCA_PROGRAM_ID = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"  # Orca Whirlpools

RAYDIUM_SOL_USDC_POOL = "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv"
ORCA_SOL_USDC_POOL = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"
