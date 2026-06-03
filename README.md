# vigmykd-server
very intense game makes your keyboard die, but it's the game server

# proto compilation
compile .proto files like this (example):
```bash
pwd
> ~/vigmykd-server
protoc --python_out=.\src\server\generated\. .\proto\v1\packet.proto
```