import asyncio
import base64
import os
import websockets


class Tunnel:
    def __init__(self, token, deviceUuid, user, vpnURL, remotePort = 80):
        self.token = token
        self.deviceUuid = deviceUuid
        self.user = user
        self.vpnURL = vpnURL
        self.remotePort = remotePort
        self.wsReaderClosed = False
        
    async def initialise(self):
        reader, writer = await asyncio.open_connection(self.vpnURL, 3128)
        self.reader = reader
        self.writer = writer
        self.writer.write(self.constructProxyHeaders().encode())
        await self.writer.drain()
        firstData = await reader.read(256)
        status = self.isConnectionEstablished(firstData.decode("utf-8"))
        return status

    async def connectReaderToWriter(self, reader, writer, bufferSize=8192):
        data = await reader.read(bufferSize)
        while data:
            try:
                writer.write(data)
                await writer.drain()
                data = await reader.read(bufferSize)
            except:
                break

    async def connectWebSocketReaderToSocketWriter(self, reader, writer):
        data = await reader.recv()
        while not self.wsReaderClosed:
            if(data != None):
                if(type(data) == str):
                    data = data.encode()
                writer.write(data)
                await writer.drain()
            try:
                data = await asyncio.wait_for(reader.recv(), timeout=1)
            except:
                data = None

    async def connectSocketReaderToWebSocketWriter(self, reader, writer, bufferSize=8192):
        data = await reader.read(bufferSize)
        while data:
            await writer.send(data)
            data = await reader.read(bufferSize)
        self.wsReaderClosed = True



    
    def isConnectionEstablished(self, data):
        splitted = data.split("\r\n")
        if(len(splitted) > 0):
            first = splitted[0].split(" ")
            if(len(first) > 1 and first[1] == "200"):
                return True
            return False
        return False


    def constructProxyHeaders(self):
        auth = {
			"user": self.user,
			"password": self.token,
		}
        credentials = base64.b64encode(f"{auth['user']}:{auth['password']}".encode("utf-8")).decode("utf-8")
        httpHeaders = [
            f"CONNECT {self.deviceUuid}.balena:{self.remotePort} HTTP/1.0",
            f"Proxy-Authorization: Basic {credentials}"
        ]
        header = '\r\n'.join(httpHeaders) + '\r\n\r\n'
        return header

class TCPConnectionServer:
    def __init__(self, localHost, localPort, token, deviceUUID, remotePort, user, vpnURL):
        self.localHost = localHost
        self.localPort = localPort
        self.token = token
        self.deviceUUID = deviceUUID
        self.remotePort = remotePort
        self.user = user
        self.vpnURL = vpnURL
    
    async def initialise(self):
        server = await asyncio.start_server(self.handleIncomingConnection, self.localHost, self.localPort)
        return server

    async def handleIncomingConnection(self, reader, writer):
        tunnel = Tunnel(self.token, self.deviceUUID, self.user, self.vpnURL, self.remotePort)
        initialized = await tunnel.initialise()
        if(initialized):
            await asyncio.gather(
                asyncio.create_task(tunnel.connectReaderToWriter(tunnel.reader, writer)),
                asyncio.create_task(tunnel.connectReaderToWriter(reader, tunnel.writer))
            )

class WebSocketConnectionServer:
    def __init__(self, localHost, localPort, token, deviceUUID, remotePort, user, vpnURL):
        self.localHost = localHost
        self.localPort = localPort
        self.token = token
        self.deviceUUID = deviceUUID
        self.remotePort = remotePort
        self.user = user
        self.vpnURL = vpnURL
    
    def initialise(self):
        server = websockets.serve(self.handleIncomingConnection, self.localHost, self.localPort)
        return server

    async def handleIncomingConnection(self, websocket, path):
        tunnel = Tunnel(self.token, self.deviceUUID, self.user, self.vpnURL, self.remotePort)
        initialized = await tunnel.initialise()
        if(initialized):
            await asyncio.gather(
                asyncio.create_task(tunnel.connectWebSocketReaderToSocketWriter(websocket, tunnel.writer)),
                asyncio.create_task(tunnel.connectSocketReaderToWebSocketWriter(tunnel.reader, websocket))
            )