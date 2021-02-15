import asyncio
import ssl
import codecs
import base64
import logging
from typing import Tuple
from asyncio.streams import StreamReader, StreamWriter
from urllib.parse import urlparse
from redis_client import get_target_location
from config import SERVER_CERT, SERVER_KEY, LISTEN_HOST, LISTEN_PORT

server = None

async def handle_stream(reader: StreamReader, writer: StreamWriter):
    try:
        while server.is_serving():
            data = await asyncio.wait_for(reader.read(4096), 60)
            if data == b'': return
            writer.write(data)
            await writer.drain()
    except:
        return

async def handle_proxy(rec_reader: StreamReader,rec_writer: StreamWriter,target_reader: StreamReader, target_writer: StreamWriter):
    to_target_handle = handle_stream(rec_reader, target_writer)
    from_target_handle = handle_stream(target_reader, rec_writer)
    
    finished, unfinished = await asyncio.wait((to_target_handle, from_target_handle))
    
    try:
        for task in unfinished:
            task.cancel()
    except: pass


async def connect_to_vpn(connect_key: str) -> Tuple[StreamReader, StreamWriter]:
    target = await get_target_location(connect_key)
    if target == None:
        logging.debug(f" [{connect_key}] target not found")
        return None
    
    # Make request to the VPN server and ask for establishing tunnel
    auth = {
		"user": target.username,
		"password": target.token,
	}
    credentials = base64.b64encode(f"{auth['user']}:{auth['password']}".encode("utf-8")).decode("utf-8")
    httpHeaders = [
        f"CONNECT {target.device_uuid}.balena:{target.device_port} HTTP/1.0",
        f"Proxy-Authorization: Basic {credentials}"
    ]
    header = '\r\n'.join(httpHeaders) + '\r\n\r\n'

    try:
        reader, writer = await asyncio.open_connection(target.url, target.port)
        writer.write(header.encode())
        await writer.drain()
    except Exception as e:
        logging.error(f"FAILED to establish connection with VPN server. {target.url}:{target.port}. " + str(e))
        return None

    #wait for response and decode
    data = ''
    try:
        firstData = await asyncio.wait_for(reader.read(256), timeout=4)
        try:
            data = firstData.decode()
        except:
            logging.error(f"Connection failed with VPN server {target.url}:{target.port}. Failed to handshake decode data. Partial data?")
            writer.close()
            return None
    except asyncio.TimeoutError:
        logging.error(f"Connection failed with VPN server {target.url}:{target.port}. Timeout.")
        writer.close()
        return None

    #Check if response is positive
    try:
        splitted = data.split("\r\n")
        first = splitted[0].split(" ")
        assert first[1] == "200"
        return (reader, writer)
    except Exception as e:
        logging.error(f"Negative response for establishing connection to VPN server. {target.url}:{target.port}. " + str(e))
        logging.debug(data)
        writer.close()
        return None

async def handle_connection(reader: StreamReader, writer: StreamWriter):
    #Waiting for headers
    data = b''
    try:
        data = await asyncio.wait_for(reader.read(256), timeout=4)
    except asyncio.TimeoutError:
        logging.debug(f"New connection closed, because header wasnt received in time.")
        writer.close()
        return

    #Find target host
    connect_key = ''
    dec = codecs.getincrementaldecoder('utf8')()
    part_headers = dec.decode(data)
    try:
        host_start = part_headers.find("Host: ")
        host_end = part_headers.find("\n", host_start)
        host_header = part_headers[host_start: host_end]
        host = host_header.split(" ")[1]
        connect_key = host.split(".")[0]
        print(connect_key)
    except Exception as e:
        logging.debug(f"New connection with invalid HOST data: " + str(e))
        writer.close()
        return
    logging.debug(f" [{connect_key}] new connection")

    #Establish
    connection_result = await connect_to_vpn(connect_key)
    if connection_result == None:
        writer.close()
        return
    (target_reader, target_writer) = connection_result
    logging.debug(f" [{connect_key}] connected to the vpn")

    #Send already received data to the target
    try:
        target_writer.write(data)
        await writer.drain()
    except:
        logging.debug(f" [{connect_key}] failed to write initial data")
        writer.close()
        target_writer.close()

    #handle
    logging.debug(f" [{connect_key}] proxy started")
    await handle_proxy(reader, writer, target_reader, target_writer)

    #clean and exit
    try:
        writer.close()
    except: pass
    try:
        target_writer.close()
    except: pass
    logging.debug(f" [{connect_key}] closed")

async def start_server():
    secured_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    secured_context.options |= ssl.OP_NO_TLSv1
    secured_context.options |= ssl.OP_NO_TLSv1_1
    secured_context.options |= ssl.OP_SINGLE_DH_USE
    secured_context.options |= ssl.OP_SINGLE_ECDH_USE
    secured_context.load_cert_chain(SERVER_CERT, keyfile=SERVER_KEY)
    secured_context.check_hostname = False

    global server
    server = await asyncio.start_server(handle_connection, LISTEN_HOST, LISTEN_PORT, ssl=secured_context)

    logging.info(f"Started server on {server.sockets[0].getsockname()}")

    async with server:
        await server.serve_forever()