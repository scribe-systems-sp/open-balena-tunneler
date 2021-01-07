import requests
import docker
from fastapi.testclient import TestClient
import sys
import os

from api.src.main import app
from api.src.config.config import *

import time


client = TestClient(app)
LOGIN=os.environ.get("LOGIN", None)
PASSWORD=os.environ.get("PASSWORD", None)
TESTDEVICEUUID=os.environ.get("TESTDEVICEUUID", None)

# Shit testing is still better testing that no testing


def test_bad_authorization():
    response = client.post("/connections", headers={"Authorization": "Bearer asdass"})
    assert response.status_code == 401
    response = client.post("/connections")
    assert response.status_code == 401

def test_good_authorization():
    tokenReq = requests.post(f"https://api.{openBalena}/login_", json={"username": LOGIN, "password": PASSWORD})
    assert tokenReq.status_code == 200
    token = tokenReq.text
    response = client.post("/connections", headers={"Authorization": f"Bearer {token}"}, json={})
    assert response.status_code == 200

def test_tcp_connection():
    tokenReq = requests.post(f"https://api.{openBalena}/login_", json={"username": LOGIN, "password": PASSWORD})
    assert tokenReq.status_code == 200
    token = tokenReq.text
    req = {
        "deviceUUID": TESTDEVICEUUID,
        "remotePort": 80
    }
    response = client.post("/requestConnection", headers={"Authorization": f"Bearer {token}"}, json=req)
    assert response.status_code == 422
    req = {
        "deviceUUID": TESTDEVICEUUID,
        "remotePort": 48484,
        "localPort": 9911
    }
    response = client.post("/requestConnection", headers={"Authorization": f"Bearer {token}"}, json=req)
    assert response.status_code == 200
    time.sleep(5)
    # Supervisor will return 401
    rr = requests.get("http://localhost:9911")
    assert rr.status_code == 401

def test_connection_exists():
    tokenReq = requests.post(f"https://api.{openBalena}/login_", json={"username": LOGIN, "password": PASSWORD})
    assert tokenReq.status_code == 200
    token = tokenReq.text
    req = {
        "deviceUUID": TESTDEVICEUUID
    }
    response = client.post("/connections", headers={"Authorization": f"Bearer {token}"}, json=req)
    assert response.status_code == 200
    jsoned = response.json()
    assert len(jsoned) > 0
    assert jsoned[0]["forwarderType"] == "TCP"
    assert jsoned[0]["deviceUUID"] == TESTDEVICEUUID
    assert jsoned[0]["remotePort"] == "48484"

def test_remove_all_on_device():
    tokenReq = requests.post(f"https://api.{openBalena}/login_", json={"username": LOGIN, "password": PASSWORD})
    assert tokenReq.status_code == 200
    token = tokenReq.text
    req = {
        "deviceUUID": TESTDEVICEUUID
    }
    response = client.post("/stopConnection", headers={"Authorization": f"Bearer {token}"}, json=req)
    assert response.status_code == 200