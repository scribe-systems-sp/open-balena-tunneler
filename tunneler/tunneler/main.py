from .lib.tunneler import TCPConnectionServer
import os
import asyncio
from webssh.main import main as websshmain
import sys

bindTo = os.environ.get("BIND", "0.0.0.0")
allocatePort = os.environ.get("ALLOCATE", 9999)
token = os.environ["TOKEN"]
deviceUUID = os.environ.get("DEVICEUUID")
remotePort = os.environ.get("REMOTEPORT", 80)
user = os.environ.get("USER", "root")
openBalena = os.environ["OPENBALENA"]
connectionType = os.environ["CONNECTIONTYPE"]
async def main():
    if(connectionType == "TCP"):
        ic = TCPConnectionServer(bindTo, allocatePort, token, deviceUUID, remotePort, user, f"vpn.{openBalena}")
        server  = await ic.initialise()
        await server.serve_forever()
    elif(connectionType == "SSH"):
        ic = TCPConnectionServer(bindTo, int(allocatePort) - 1, token, deviceUUID, remotePort, user, f"vpn.{openBalena}")
        server  = await ic.initialise()
        await server.start_serving()
        sys.argv.append(f"--port={allocatePort}")
        sys.argv.append(f"--timeout=60")
        websshmain()

asyncio.get_event_loop().run_until_complete(main())
asyncio.get_event_loop().run_forever()
