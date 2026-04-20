FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential cmake ninja-build python3 python3-pip git libssl-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
