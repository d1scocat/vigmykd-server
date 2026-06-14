FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y protobuf-compiler && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN mkdir -p src/server/generated

RUN protoc \
    --proto_path=proto \
    --python_out=src/server/generated \
    proto/v1/packet.proto

RUN pip install --no-cache-dir .

RUN useradd --create-home --shell /usr/sbin/nologin server
RUN chown -R server:server /app

USER server

CMD ["python", "-m", "server.main"]