import asyncore
import base64

class Tunnel(asyncore.dispatcher):
    def __init__(self, client, token, deviceUuid, user, vpnURL, remotePort):
        asyncore.dispatcher.__init__(self)
        self.client = client
        self.create_socket()
        self.connect( (vpnURL, 3128) )
        auth = {
			"user": user,
			"password": token,
		}
        credentials = base64.b64encode(f"{auth['user']}:{auth['password']}".encode("utf-8")).decode("utf-8")
        httpHeaders = [
            f"CONNECT {deviceUuid}.balena:{remotePort} HTTP/1.0",
            f"Proxy-Authorization: Basic {credentials}"
        ]
        header = '\r\n'.join(httpHeaders) + '\r\n\r\n'
        self.proxyBuffer = bytes(header, 'ascii')
        self.readBuffer = bytes()
        self.writeBuffer = bytes()
        self.initialized = False

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        data = self.recv(8192)
        if(data and self.initialized):
            self.writeBuffer = self.writeBuffer + bytes(data)
        elif(not self.initialized):
            decoded = data.decode("utf-8")
            if("200 Connection Established\r\nProxy-agent: balena-io" in decoded):
                self.initialized = True

    def writable(self):
        return (len(self.proxyBuffer) > 0 or (len(self.readBuffer) > 0 and self.initialized))

    def handle_write(self):
        if(len(self.proxyBuffer) > 0):
            sent = self.send(self.proxyBuffer)
            self.proxyBuffer = self.proxyBuffer[sent:]
        elif(len(self.readBuffer) > 0 and self.initialized):
            sent = self.send(self.readBuffer)
            self.readBuffer = self.readBuffer[sent:]

class ClientHandler(asyncore.dispatcher_with_send):
    def __init__(self, sock, token, deviceUUID, remotePort):
        self.tunnel = Tunnel(self, token, deviceUUID, remotePort=remotePort)
        asyncore.dispatcher_with_send.__init__(self, sock)
        self.buffer = bytes()

    def handle_read(self):
        data = self.socket.recv(8192)
        if(data):
            self.tunnel.readBuffer = self.tunnel.readBuffer + bytes(data)

    def writable(self):
        return (len(self.tunnel.writeBuffer) > 0)

    def handle_write(self):
        sent = self.socket.send(self.tunnel.writeBuffer)
        self.tunnel.writeBuffer = self.tunnel.writeBuffer[sent:]

    def handle_close(self):
        self.close()

class Server(asyncore.dispatcher):
    def __init__(self, token, deviceUuid, localHost, localPort, remotePort):
        asyncore.dispatcher.__init__(self)
        self.create_socket()
        self.set_reuse_addr()
        self.bind((localHost, localPort))
        self.listen(5)
        self.deviceUUID = deviceUuid
        self.remotePort = remotePort
        self.token = token

    def handle_accepted(self, sock, addr):
        handler = ClientHandler(sock, self.token, self.deviceUUID, self.remotePort)
    
