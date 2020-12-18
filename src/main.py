from fastapi import FastAPI, BackgroundTasks, Header, Depends
from fastapi.exceptions import HTTPException
from .config.config import *
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
import aiohttp
from pydantic import BaseModel
import docker

app = FastAPI()
server = None

async def isTokenOk(authorization: Optional[str] = Header(None)):
    if(authorization):
        if(authorization.startswith("Bearer ")):
            url = f"https://api.{openBalena}/v6/my_application"
            try:
                async with aiohttp.ClientSession(headers = {"Authorization": authorization}) as session:
                    async with session.get(url) as response:
                        if(response.status == 200):
                            return authorization[7:]
                        else:
                            raise HTTPException(401, "Bad status code")
            except:
                raise HTTPException(401, "Bad response from login")

        else:
            raise HTTPException(401, "Bad token")
    else:
        raise HTTPException(401, "No token provided")

async def createTCPConnection(token, deviceUUID, port, allocatePort):
    client = docker.from_env()
    client.containers.run(
        "tunneler", 
        detach = True, 
        environment = {"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port, "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "TCP"}, 
        restart_policy = {"Name": "always"},
        ports = {
            "9999/tcp": allocatePort
        },
        labels = {
            "belongsTo": "OpenBalenaForwarder",
            "deviceUUID": deviceUUID,
            "remotePort": str(port),
            "localPort": str(allocatePort),
            "forwarderType": "TCP"
        },
        name=f"TCP.{deviceUUID}.{port}.{allocatePort}"
    )

async def createSSHConnection(token, deviceUUID, port, allocatePort):
    client = docker.from_env()
    client.containers.run(
        "tunneler", 
        detach = True, 
        environment = {"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port, "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "SSH"}, 
        restart_policy = {"Name": "always"},
        ports = {
            "9999/tcp": allocatePort
        },
        labels = {
            "belongsTo": "OpenBalenaForwarder",
            "deviceUUID": deviceUUID,
            "remotePort": str(port),
            "localPort": str(allocatePort),
            "forwarderType": "SSH"
        },
        name=f"SSH.{deviceUUID}.{port}.{allocatePort}"
    )

async def createTraefikSSHConnection(token, deviceUUID, domainName, port, traefikNetwork, useXIP):
    client = docker.from_env()
    if(useXIP):
        domainName = domainName + "." + publicIp + ".xip.io"
    client.containers.run(
        "tunneler", 
        detach = True, 
        environment = {"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port, "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "SSH"}, 
        restart_policy = {"Name": "always"},
        network = traefikNetwork,
        labels = {
            "belongsTo": "OpenBalenaForwarder",
            "deviceUUID": deviceUUID,
            "remotePort": str(port),
            "forwarderType": "SSHTRAEFIK",
            "domainName": domainName,
            f"traefik.http.routers.{deviceUUID}{port}.rule" : f"Host(`{domainName}`)"
        },
        name=f"SSHTRAEFIK.{deviceUUID}.{port}.{domainName}"
    )


async def createTraefikConnection(token, deviceUUID, domainName, port, traefikNetwork, useXIP):
    client = docker.from_env()
    if(useXIP):
        domainName = domainName + "." + publicIp + ".xip.io"
    client.containers.run(
        "tunneler", 
        detach = True, 
        environment = {"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port, "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "TCP"}, 
        restart_policy = {"Name": "always"},
        network = traefikNetwork,
        labels = {
            "belongsTo": "OpenBalenaForwarder",
            "deviceUUID": deviceUUID,
            "remotePort": str(port),
            "forwarderType": "TRAEFIK",
            "domainName": domainName,
            f"traefik.http.routers.{deviceUUID}{port}.rule" : f"Host(`{domainName}`)"
        },
        name=f"TRAEFIK.{deviceUUID}.{port}.{domainName}"
    )



class RequestConnection(BaseModel):
    deviceUUID: str
    remotePort: int
    localPort: int
    forwarderType: str = "TCP"
    additionalSettings: dict = dict()

class StopConnection(BaseModel):
    forwarderType: str = None
    localPort: int = None
    remotePort: int = None
    deviceUUID: str = None
    additionalSettings: dict = dict()


def getContainers(deviceUUID = None, forwarderType = None, localPort = None, remotePort = None, additionalSettings = dict(), sparse=True):
    labels = ["belongsTo=OpenBalenaForwarder"]
    if(deviceUUID):
        labels.append(f"deviceUUID={deviceUUID}")
    if(forwarderType):
        labels.append(f"forwarderType={deviceUUID}")
    if(localPort):
        labels.append(f"localPort={deviceUUID}")
    if(remotePort):
        labels.append(f"remotePort={deviceUUID}")
    if(additionalSettings):
        for key in additionalSettings.keys():
            labels.append(f"{key}={additionalSettings[key]}")
    client = docker.from_env()
    containers = client.containers.list(sparse=sparse, all=True, filters={"label": ["belongsTo=OpenBalenaForwarder"]})
    return containers


@app.post("/requestConnection")
async def requestConnection(req: RequestConnection, token = Depends(isTokenOk)):
    if(req.forwarderType == "TCP"):
        await createTCPConnection(token, req.deviceUUID, req.remotePort, req.localPort)
    elif(req.forwarderType == "TRAEFIK"):
        domainName = req.additionalSettings.get("domainName", None)
        useXIP = req.additionalSettings.get("useXIP", False)
        traefikNetwork = req.additionalSettings.get("traefikNetwork", "web")
        await createTraefikConnection(token, req.deviceUUID, domainName, req.remotePort, traefikNetwork, useXIP)
    elif(req.forwarderType == "SSH"):
        await createSSHConnection(token, req.deviceUUID, req.remotePort, req.localPort)
    elif(req.forwarderType == "SSHTRAEFIK"):
        domainName = req.additionalSettings.get("domainName", None)
        useXIP = req.additionalSettings.get("useXIP", False)
        traefikNetwork = req.additionalSettings.get("traefikNetwork", "web")
        await createTraefikSSHConnection(token, req.deviceUUID, domainName, req.remotePort, traefikNetwork, useXIP)
    else:
        raise HTTPException(400, "Forwarder type not supported")
    return {"ip": publicIp, "port": req.localPort, "forwarderType": req.forwarderType}


@app.post("/stopConnection")
async def stopConnection(req: StopConnection, token = Depends(isTokenOk)):
    containers = getContainers(forwarderType=req.forwarderType, localPort=req.localPort, deviceUUID=req.deviceUUID, remotePort=req.remotePort, additionalSettings=req.additionalSettings)
    for container in containers:
        container.remove(force=True)
    return {"status": "Connection closed", "killed": len(containers)}


@app.post("/connections")
async def getServices(req: StopConnection, token = Depends(isTokenOk)):
    containers = getContainers(forwarderType=req.forwarderType, localPort=req.localPort, deviceUUID=req.deviceUUID, remotePort=req.remotePort, additionalSettings=req.additionalSettings, sparse=False)
    toRet = []
    for container in containers:
        labels = container.labels
        toRet.append(labels)
    return toRet
