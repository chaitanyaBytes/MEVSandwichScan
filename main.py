import asyncio
import config
from solana.rpc.async_api import AsyncClient


async def main():
    rpc_url = config.RPC_ENDPOINT
    if not rpc_url:
        print("ERROR: RPC URL is missing in the .env file")
        return

    print(rpc_url)

    async with AsyncClient(rpc_url) as client:
        res = await client.is_connected()
        print(res)  # True


try:
    asyncio.run(main())
except Exception as e:
    print(f"ERROR: {e}")
