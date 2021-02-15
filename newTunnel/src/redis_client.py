import aioredis
import json
import logging

from config import REDIS_URL

redis_client: aioredis.Redis = None

class TargetData():
    def __init__(self, url: str, port: int, username: str, token: str, device_uuid: str, device_port: int) -> None:
        self.url = url
        self.port = port

        self.token = token
        self.username = username

        self.device_uuid = device_uuid
        self.device_port = device_port

async def get_target_location(connection_key: str) -> TargetData:
    try:
        response = await redis_client.get(connection_key, encoding='utf-8')
        if response == None:
            return None

        try:
            json_data = json.loads(response)
            return TargetData(
                str(json_data["url"]),
                int(json_data["port"]),
                str(json_data["username"]),
                str(json_data["token"]),
                str(json_data["device_uuid"]),
                int(json_data["device_port"])
            )
        except ValueError:
            logging.error(f"Redis data for [{connection_key}] has fields with incorrect data format. (string instead of integer ?). Received: {json_data}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Redis data for [{connection_key}] is not in json format. " + str(e))
            return None
        except KeyError:
            logging.error(f"Redis data for [{connection_key}] doesnt have required fields. Received: {json_data}")
            return None
        
    except Exception as e:
        logging.error("Failed to get info from redis. " + str(e))
        return None

async def init():
    global redis_client
    redis_client = await aioredis.create_redis_pool(REDIS_URL)
    logging.info(f"Connected to redis at {REDIS_URL}")

async def close():
    redis_client.close()
    await redis_client.wait_closed()
    logging.info(f"Disconnected from redis")