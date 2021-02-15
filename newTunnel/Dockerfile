FROM python:3.8
RUN pip install uvloop aioredis
COPY src /app
VOLUME /certs
ENV LISTEN_HOST 0.0.0.0
ENV LISTEN_PORT 443
ENV SERVER_CERT /certs/server.cert
ENV SERVER_KEY /certs/server.key
ENV REDIS_URL redis://redis
ENTRYPOINT ["python", "/app/main.py"]