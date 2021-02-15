from os import environ

REDIS_URL = environ.get("REDIS_URL", 'redis://localhost')

LISTEN_HOST = environ.get("LISTEN_HOST", '0.0.0.0')
LISTEN_PORT = int(environ.get("LISTEN_PORT", 8888))

SERVER_CERT = environ.get("SERVER_CERT", 'server.cert')
SERVER_KEY = environ.get("SERVER_KEY", 'server.key')