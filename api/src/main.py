from fastapi import FastAPI, BackgroundTasks, Header, Depends
from fastapi.exceptions import HTTPException
from .config.config import *
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Optional
import aiohttp
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uuid

import docker

app = FastAPI()
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
server = None


async def isTokenOk(authorization: Optional[str] = Header(None)):
    if(authorization):
        if(authorization.startswith("Bearer ")):
            url = f"https://api.{openBalena}/v6/my_application"
            try:
                async with aiohttp.ClientSession(headers={"Authorization": authorization}) as session:
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


async def createTCPConnection(token, deviceUUID, port, allocatePort, labels):
    uuid4 = str(uuid.uuid4())
    shortUUID = uuid4[0:8]
    client = docker.from_env()
    mainLabels = {
        "belongsTo": "OpenBalenaForwarder",
        "deviceUUID": deviceUUID,
        "remotePort": str(port),
        "localPort": str(allocatePort),
        "forwarderType": "TCP",
        "uuid": uuid4
    }
    client.containers.run(
        "tunneler",
        detach=True,
        environment={"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port,
                     "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "TCP"},
        restart_policy={"Name": "always"},
        ports={
            "9999/tcp": allocatePort
        },
        labels={**labels, **mainLabels},
        name=f"TCP.{deviceUUID}.{port}.{allocatePort}.{shortUUID}"
    )


async def createSSHConnection(token, deviceUUID, port, allocatePort, labels):
    uuid4 = str(uuid.uuid4())
    shortUUID = uuid4[0:8]
    client = docker.from_env()
    mainlabels = {
        "belongsTo": "OpenBalenaForwarder",
        "deviceUUID": deviceUUID,
        "remotePort": str(port),
        "localPort": str(allocatePort),
        "forwarderType": "SSH",
        "uuid": uuid4
    }
    client.containers.run(
        "tunneler",
        detach=True,
        environment={"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port,
                     "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "SSH"},
        restart_policy={"Name": "always"},
        ports={
            "9999/tcp": allocatePort
        },
        labels={**labels, **mainlabels},
        name=f"SSH.{deviceUUID}.{port}.{allocatePort}.{shortUUID}"
    )


async def createTraefikSSHConnection(token, deviceUUID, domainName, port, traefikNetwork, useXIP, labels):
    uuid4 = str(uuid.uuid4())
    shortUUID = uuid4[0:8]
    client = docker.from_env()
    if(useXIP):
        domainName = domainName + "." + publicIp + ".xip.io"
    mainlabels = {
        "belongsTo": "OpenBalenaForwarder",
        "deviceUUID": deviceUUID,
        "remotePort": str(port),
        "forwarderType": "SSHTRAEFIK",
        "domainName": domainName,
        f"traefik.http.routers.{deviceUUID}{port}{shortUUID}.rule": f"Host(`{domainName}`)",
        "uuid": uuid4
    }
    client.containers.run(
        "tunneler",
        detach=True,
        environment={"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port,
                     "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "SSH"},
        restart_policy={"Name": "always"},
        network=traefikNetwork,
        labels={**labels, **mainlabels},
        name=f"SSHTRAEFIK.{deviceUUID}.{port}.{domainName}.{shortUUID}"
    )


async def createTraefikConnection(token, deviceUUID, domainName, port, traefikNetwork, useXIP, labels):
    uuid4 = str(uuid.uuid4())
    shortUUID = uuid4[0:8]
    client = docker.from_env()
    if(useXIP):
        domainName = domainName + "." + publicIp + ".xip.io"
    mainlabels = {
        "belongsTo": "OpenBalenaForwarder",
        "deviceUUID": deviceUUID,
        "remotePort": str(port),
        "forwarderType": "TRAEFIK",
        "domainName": domainName,
        f"traefik.http.routers.{deviceUUID}{port}{shortUUID}.rule": f"Host(`{domainName}`)",
        "uuid": uuid4
    }
    client.containers.run(
        "tunneler",
        detach=True,
        environment={"TOKEN": token, "DEVICEUUID": deviceUUID, "REMOTEPORT": port,
                     "OPENBALENA": openBalena, "ALLOCATE": 9999, "CONNECTIONTYPE": "TCP"},
        restart_policy={"Name": "always"},
        network=traefikNetwork,
        labels={**labels, **mainlabels},
        name=f"TRAEFIK.{deviceUUID}.{port}.{domainName}.{shortUUID}"
    )


class RequestConnection(BaseModel):
    deviceUUID: str
    remotePort: int
    localPort: int = None
    forwarderType: str = "TCP"
    additionalSettings: dict = dict()
    additionalLabels: dict = dict()


class StopConnection(BaseModel):
    forwarderType: str = None
    localPort: int = None
    remotePort: int = None
    deviceUUID: str = None
    additionalSettings: dict = dict()
    additionalLabels: dict = dict()


def getContainers(deviceUUID=None, forwarderType=None, localPort=None, remotePort=None, additionalSettings=dict(), additionalLabels=dict(), sparse=True):
    labels = ["belongsTo=OpenBalenaForwarder"]
    if(deviceUUID):
        labels.append(f"deviceUUID={deviceUUID}")
    if(forwarderType):
        labels.append(f"forwarderType={forwarderType}")
    if(localPort):
        labels.append(f"localPort={localPort}")
    if(remotePort):
        labels.append(f"remotePort={remotePort}")
    if(additionalSettings):
        for key in additionalSettings.keys():
            labels.append(f"{key}={additionalSettings[key]}")
    if(additionalLabels):
        for key in additionalLabels.keys():
            labels.append(f"{key}={additionalLabels[key]}")
    client = docker.from_env()
    containers = client.containers.list(
        sparse=sparse, all=True, filters={"label": labels})
    return containers


@app.post("/requestConnection")
async def requestConnection(req: RequestConnection, token=Depends(isTokenOk)):
    if(req.forwarderType == "TCP"):
        if(req.localPort == None):
            raise HTTPException(422, "Pass localPort")
        await createTCPConnection(token, req.deviceUUID, req.remotePort, req.localPort, req.additionalLabels)
    elif(req.forwarderType == "TRAEFIK"):
        domainName = req.additionalSettings.get("domainName", None)
        useXIP = req.additionalSettings.get("useXIP", False)
        traefikNetwork = req.additionalSettings.get("traefikNetwork", "web")
        await createTraefikConnection(token, req.deviceUUID, domainName, req.remotePort, traefikNetwork, useXIP, req.additionalLabels)
    elif(req.forwarderType == "SSH"):
        if(req.localPort == None):
            raise HTTPException(422, "Pass localPort")
        await createSSHConnection(token, req.deviceUUID, req.remotePort, req.localPort, req.additionalLabels)
    elif(req.forwarderType == "SSHTRAEFIK"):
        domainName = req.additionalSettings.get("domainName", None)
        useXIP = req.additionalSettings.get("useXIP", False)
        traefikNetwork = req.additionalSettings.get("traefikNetwork", "web")
        await createTraefikSSHConnection(token, req.deviceUUID, domainName, req.remotePort, traefikNetwork, useXIP, req.additionalLabels)
    else:
        raise HTTPException(400, "Forwarder type not supported")
    return {"ip": publicIp, "req": req}


@app.post("/stopConnection")
async def stopConnection(req: StopConnection, token=Depends(isTokenOk)):
    containers = getContainers(forwarderType=req.forwarderType, localPort=req.localPort, deviceUUID=req.deviceUUID,
                               remotePort=req.remotePort, additionalSettings=req.additionalSettings, additionalLabels=req.additionalLabels)
    for container in containers:
        container.remove(force=True)
    return {"status": "Connection closed", "killed": len(containers)}


@app.post("/connections")
async def getServices(req: StopConnection, token=Depends(isTokenOk)):
    containers = getContainers(forwarderType=req.forwarderType, localPort=req.localPort, deviceUUID=req.deviceUUID,
                               remotePort=req.remotePort, additionalSettings=req.additionalSettings, additionalLabels=req.additionalLabels, sparse=False)
    toRet = []
    for container in containers:
        labels = container.labels
        toRet.append(labels)
    return toRet
