import os

RPC_ENDPOINT = os.getenv("MAINNET_RPC_URL", "https://api.mainnet-beta.solana.com")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", None)

if HELIUS_API_KEY:
    RPC_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"


ANALYSIS_WINDOW_SECONDS = 7 * 24 * 60 * 60
