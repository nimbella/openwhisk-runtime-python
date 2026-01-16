#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# --- BUILDER STAGE: Compile the Go Proxy ---
ARG GO_PROXY_BASE_IMAGE=golang:1.20
FROM $GO_PROXY_BASE_IMAGE AS builder

# Use the standard Apache repository and the correct branch ('master')
ARG GO_PROXY_GITHUB_USER=apache
ARG GO_PROXY_GITHUB_BRANCH=master

RUN git clone --branch ${GO_PROXY_GITHUB_BRANCH} https://github.com/${GO_PROXY_GITHUB_USER}/openwhisk-runtime-go /src \
  && cd /src \
  && env GO111MODULE=on CGO_ENABLED=0 go build -o /bin/proxy main/proxy.go

# --- RUNTIME STAGE: Python 3.11 ---
FROM python:3.11-slim-bullseye

# select the builder to use
ARG GO_PROXY_BUILD_FROM=release

# --- FIX: Install build tools for daft 0.4.8 source build ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    build-essential \
    python3-dev \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add Bun and Rust to the PATH
ENV PATH="/root/.bun/bin:/root/.cargo/bin:${PATH}"
# --- END FIX ---

# Install common modules for python
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# install the functions-deployer
# ADDED DEFAULT VALUE HERE TO FIX THE CURL ERROR
ARG DEPLOYER_DOWNLOAD=https://do-serverless-tools.nyc3.digitaloceanspaces.com/dosls-5.0.22.tgz
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -L ${DEPLOYER_DOWNLOAD} | tar xzf - \
  && rm -fr /usr/local/lib/dosls && mv dosls /usr/local/lib \
  && rm -f /usr/local/bin/dosls && ln -s /usr/local/lib/dosls/bootstrap /usr/local/bin/dosls

RUN mkdir -p /action
WORKDIR /
COPY bin/compile /bin/compile
COPY lib/launcher.py /lib/launcher.py
COPY lib/prelauncher.py /lib/prelauncher.py

# log initialization errors
ENV OW_LOG_INIT_ERROR=1
# the launcher must wait for an ack
ENV OW_WAIT_FOR_ACK=1
# compiler script
ENV OW_COMPILER=/bin/compile

ENV OW_INIT_IN_ACTIONLOOP=/lib/prelauncher.py

COPY --from=builder /bin/proxy /bin/proxy
ENTRYPOINT ["/bin/proxy"]

