#!/usr/local/bin/python

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
from __future__ import print_function
from sys import stdin
from sys import stdout
from sys import stderr
from os import fdopen
import sys, os, json, traceback, base64, io, zipfile

log_sentinel="XXX_THE_END_OF_A_WHISK_ACTIVATION_XXX\n"
def write_sentinels():
  stdout.write(log_sentinel)
  stderr.write(log_sentinel)
  stdout.flush()
  stderr.flush()

out = fdopen(3, "wb")
def write_result(res):
  out.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
  out.write(b'\n')
  out.flush()

def cannot_start(msg):
  stderr.write(msg)
  write_result({"error": "Cannot start action. Check logs for details."})
  write_sentinels()
  sys.exit(1)

# Notify the Golang proxy that the process is awaiting input.
write_result({"ok": True})

# Read the init payload.
line = stdin.readline()
init = json.loads(line)["value"]

# Set the environment from the init payload.
if init["env"]:
  for key, value in init["env"].items():
    if isinstance(value, str):
      os.environ[key] = value
    else:
      # Anything that's not a string needs to be stringified.
      os.environ[key] = json.dumps(value)

if init["binary"]:
  # We have a base64 encoded zip as code.
  buffer = base64.b64decode(init["code"])
  with zipfile.ZipFile(io.BytesIO(buffer)) as zip_ref:
    zip_ref.extractall(".")

  # Note: We're ignoring `exec` here as we don't need a starter script.
  if os.path.exists("__main__.py"):
    os.rename("__main__.py", "main__.py")
  if not os.path.exists("main__.py"):
    cannot_start("Zip file does not include '__main__.py'.\n")

  try:
    # If the directory 'virtualenv' is extracted out of a zip file.
    path_to_virtualenv = os.path.abspath('virtualenv')
    if os.path.isdir(path_to_virtualenv):
      # Activate the virtualenv using activate_this.py contained in the virtualenv.
      activate_this_file = path_to_virtualenv + '/bin/activate_this.py'
      if not os.path.exists(activate_this_file): # try windows path
        activate_this_file = path_to_virtualenv + '/Scripts/activate_this.py'
      if os.path.exists(activate_this_file):
        exec(open(activate_this_file).read(), {'__file__': activate_this_file})
      else:
        cannot_start("Invalid virtualenv: Zip file does not include 'activate_this.py'.\n")
  except Exception as ex:
    traceback.print_exc(file=stderr, limit=0)
    cannot_start("Invalid virtualenv: Failed to active virtualenv %s.\n" % str(ex))
else:
  # TODO: We can optimize this further by compiling the code in-process.
  with open("main__.py", mode="wb") as f:
    f.write(init["code"].encode("utf-8"))

# Import the action itself.
try:
  sys.path.append(os.getcwd())
  main = getattr(__import__("main__", fromlist=[init["main"]]), init["main"])
except Exception as ex:
  cannot_start("Invalid action: %s\n" % str(ex))

# Acknowledge the initialization.
write_result({"ok": True})

# Enter the actual action loop.
while True:
  line = stdin.readline()
  if not line: break
  args = json.loads(line)
  payload = {}
  for key in args:
    if key == "value":
      payload = args["value"]
    else:
      os.environ["__OW_%s" % key.upper()]= args[key]
  res = {}
  try:
    res = main(payload)
  except Exception as ex:
    print(traceback.format_exc(), file=stderr)
    res = {"error": str(ex)}
  write_result(res)
  write_sentinels()
