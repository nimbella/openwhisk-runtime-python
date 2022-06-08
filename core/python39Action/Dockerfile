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

# build go proxy from source
ARG GO_PROXY_BASE_IMAGE=golang:1.18
FROM $GO_PROXY_BASE_IMAGE AS builder

ARG GO_PROXY_GITHUB_USER=nimbella-corp
ARG GO_PROXY_GITHUB_BRANCH=dev
RUN git clone --branch ${GO_PROXY_GITHUB_BRANCH} https://github.com/${GO_PROXY_GITHUB_USER}/openwhisk-runtime-go /src \
  && cd /src \
  && env GO111MODULE=on CGO_ENABLED=0 go build -o /bin/proxy main/proxy.go

FROM python:3.9-slim-buster

# Install common modules for python
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# install nim
ARG NIM_INSTALL_SCRIPT=https://apigcp.nimbella.io/downloads/nim/nim-install-linux.sh
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && curl ${NIM_INSTALL_SCRIPT} | bash \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /action
WORKDIR /
COPY bin/compile /bin/compile
COPY lib/launcher.py /lib/launcher.py
COPY lib/prelauncher.py /lib/prelauncher.py

# log initialization errors
ENV OW_LOG_INIT_ERROR=1
# the launcher must wait for an ack
ENV OW_WAIT_FOR_ACK=1
# using the runtime name to identify the execution environment
#ENV OW_EXECUTION_ENV=openwhisk/action-python-v3.9
# compiler script
ENV OW_COMPILER=/bin/compile

ENV OW_INIT_IN_ACTIONLOOP=/lib/prelauncher.py

COPY --from=builder /bin/proxy /bin/proxy
ENTRYPOINT ["/bin/proxy"]
