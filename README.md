# Open Balena Tunneler

This project is compatible with https://github.com/Razikus/open-balena-dashboard

Exposes API that allows you to make tunnel between device connected to OpenBalena VPN and your server.


## Traefik install

```bash
cd traefik
docker network create web
docker-compose up -d
```

## Tunneler install

```bash
bash build.sh
# change docker-compose.yml to change BASEHREF and PUBLIC envs
# BASEHREF=your open balena instance base href like blabla.com
# PUBLIC=your ip address that will be reachable from your computer 
# like your local IP address or public IP address
docker-compose up -d 
```

## Usage

Go to http://localhost:8000/docs

Or just go to open-balena-dashboard and put http://localhost:8000 in "Tunneler URL" field