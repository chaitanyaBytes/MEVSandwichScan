import asyncio
import os
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient

load_dotenv()

async def main():
    rpc_url = os.getenv("DEVNET_RPC_URL")
    if not rpc_url: 
        print("ERROR: RPC URL is missing in the .env file")
        return

    async with AsyncClient(rpc_url) as client:
        res = await client.is_connected()
        print(res)  # True    

try:
    asyncio.run(main())
except Exception as e:
    print(f"ERROR: {e}")
