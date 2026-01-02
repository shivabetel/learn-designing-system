import asyncio


order_queue = asyncio.Queue(maxsize=100_000)