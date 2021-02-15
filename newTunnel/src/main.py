import asyncio
import uvloop
import logging

from redis_client import init as init_redis, close as close_redis 
from server import start_server

async def main():
    await init_redis()
    try:
        await start_server()
    finally:
        await close_redis()

logging.basicConfig(level = logging.INFO)
uvloop.install()
try:
    asyncio.get_event_loop().run_until_complete(main())
except KeyboardInterrupt:
    logging.info("Stopping server")