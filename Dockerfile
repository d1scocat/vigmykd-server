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

CMD ["python", "-m", "server.main"]