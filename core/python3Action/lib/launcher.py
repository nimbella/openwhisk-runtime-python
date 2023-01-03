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
import sys, os, json, traceback, time

log_sentinel="XXX_THE_END_OF_A_WHISK_ACTIVATION_XXX\n"

try:
  # if the directory 'virtualenv' is extracted out of a zip file
  path_to_virtualenv = os.path.abspath('./virtualenv')
  if os.path.isdir(path_to_virtualenv):
    # activate the virtualenv using activate_this.py contained in the virtualenv
    activate_this_file = path_to_virtualenv + '/bin/activate_this.py'
    if not os.path.exists(activate_this_file): # try windows path
      activate_this_file = path_to_virtualenv + '/Scripts/activate_this.py'
    if os.path.exists(activate_this_file):
      with open(activate_this_file) as f:
        code = compile(f.read(), activate_this_file, 'exec')
        exec(code, dict(__file__=activate_this_file))
    else:
      sys.stderr.write("Invalid virtualenv. Zip file does not include 'activate_this.py'.\n")
      sys.exit(1)
except Exception:
  traceback.print_exc(file=sys.stderr, limit=0)
  sys.exit(1)

# now import the action as process input/output
from main__ import main as main

class Context:
  def __init__(self, env):
    self.function_name = env["__OW_ACTION_NAME"]
    self.function_version = env["__OW_ACTION_VERSION"]
    self.activation_id = env["__OW_ACTIVATION_ID"]
    self.request_id = env["__OW_TRANSACTION_ID"]
    self.deadline = int(env["__OW_DEADLINE"])
    self.api_host = env["__OW_API_HOST"]
    self.api_key = env.get("__OW_API_KEY", "")
    self.namespace = env["__OW_NAMESPACE"]

  def get_remaining_time_in_millis(self):
    epoch_now_in_ms = int(time.time() * 1000)
    delta_ms = self.deadline - epoch_now_in_ms
    return delta_ms if delta_ms > 0 else 0

def fun(payload, env):
  # Compatibility: Supporting "old" context-less functions that have no params
  # to match other languages.
  if main.__code__.co_argcount == 0:
    return main() or {}
    
  # Compatibility: Supports "old" context-less functions.
  if main.__code__.co_argcount == 1:
    return main(payload) or {}

  # Lambda-like "new-style" function.
  return main(payload, Context(env)) or {}

out = fdopen(3, "wb")
if os.getenv("__OW_WAIT_FOR_ACK", "") != "":
    out.write(json.dumps({"ok": True}, ensure_ascii=False).encode('utf-8'))
    out.write(b'\n')
    out.flush()

env = os.environ
while True:
  line = stdin.readline()
  if not line: break
  args = json.loads(line)
  payload = {}
  for key in args:
    if key == "value":
      payload = args["value"]
    else:
      env["__OW_%s" % key.upper()]= args[key]
  res = {}
  try:
    res = fun(payload, env)
  except Exception as ex:
    print(traceback.format_exc(), file=stderr)
    res = {"error": str(ex)}
  out.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
  out.write(b'\n')
  stdout.write(log_sentinel)
  stderr.write(log_sentinel)
  stdout.flush()
  stderr.flush()
  out.flush()
