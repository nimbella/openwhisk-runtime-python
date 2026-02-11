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

# STAGE 1: Build Go Proxy from source
ARG GO_PROXY_BASE_IMAGE=golang:1.20
FROM $GO_PROXY_BASE_IMAGE AS proxy-builder
ARG GO_PROXY_GITHUB_USER=nimbella
ARG GO_PROXY_GITHUB_BRANCH=master
RUN git clone --branch ${GO_PROXY_GITHUB_BRANCH} https://github.com/${GO_PROXY_GITHUB_USER}/openwhisk-runtime-go /src \
  && cd /src \
  && env GO111MODULE=on CGO_ENABLED=0 go build -o /bin/proxy main/proxy.go

# STAGE 2: Build Python Wheels (Heavy Build Environment)
# This stage installs Rust, Bun, and C compilers needed only for building Daft.
FROM python:3.11-slim-bullseye AS python-builder

# Install system dependencies for building native extensions
RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    python3-dev \
    libssl-dev \
    pkg-config \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain (required for Daft engine)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Bun (required specifically for Daft Dashboard release builds)
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

WORKDIR /build
COPY requirements.txt .

# MODIFIED: Install build-time dependencies and use --no-build-isolation.
# Disabling build isolation forces pip to use the Rust/Bun toolchains we installed above,
# cutting hours off the build time and preventing redundant toolchain downloads.
RUN pip install --no-cache-dir maturin pyarrow>=8.0.0 \
    && pip wheel --no-cache-dir --no-build-isolation --wheel-dir /wheels git+https://github.com/Eventual-Inc/Daft.git@v0.4.8

# STAGE 3: Final Production Image (Slim)
FROM python:3.11-slim-bullseye
ARG GO_PROXY_BUILD_FROM=release

# Runtime dependencies only
RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy built artifacts from earlier stages
COPY --from=proxy-builder /bin/proxy /bin/proxy
COPY --from=python-builder /wheels /wheels

# Install the pre-compiled Daft wheel
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels

# MODIFIED: Filter requirements.txt to remove the 'daft' Git line.
# This prevents pip from looking for 'git' in this slim stage,
# as daft is already provided by the wheel installed in the previous step.
COPY requirements.txt requirements.txt
RUN grep -v "daft @" requirements.txt > requirements_slim.txt \
    && pip install --no-cache-dir -r requirements_slim.txt \
    && rm requirements_slim.txt

# Install the functions-deployer
ARG DEPLOYER_DOWNLOAD
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -L ${DEPLOYER_DOWNLOAD} | tar xzf - \
  && rm -fr /usr/local/lib/dosls && mv dosls /usr/local/lib \
  && rm -f /usr/local/bin/dosls && ln -s /usr/local/lib/dosls/bootstrap /usr/local/bin/dosls

# Runtime ActionLoop environment setup
RUN mkdir -p /action
WORKDIR /
COPY bin/compile /bin/compile
COPY lib/launcher.py /lib/launcher.py
COPY lib/prelauncher.py /lib/prelauncher.py

# OpenWhisk standard environment variables
# log initialization errors
ENV OW_LOG_INIT_ERROR=1
# the launcher must wait for an ack
ENV OW_WAIT_FOR_ACK=1
# compiler script
ENV OW_COMPILER=/bin/compile
ENV OW_INIT_IN_ACTIONLOOP=/lib/prelauncher.py

ENTRYPOINT ["/bin/proxy"]
