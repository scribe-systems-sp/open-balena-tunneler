import os
bindTo = os.environ.get("BIND", "0.0.0.0")
publicIp = os.environ.get("PUBLIC", "192.168.1.1")
openBalena = os.environ.get("BASEHREF", "open-balena-instance-base-url")
sslCertResolver = os.environ.get("SSLRESOLVER", "letsencrypt")
imageName = os.environ.get("IMAGENAME", "tunneler")