from flask import Flask

from .k8s_lease import run_leader_election

import os, signal

app = Flask(__name__)


@app.route("/")
def index():
    leader = state["LEADER_ID"]
    self = state["SELF_ID"]
    return f"""\
<p>Hello, World!</p>
Leader: {leader}<br>
Self: {self}<br>
"""


@app.route("/crash", methods=["POST"])
def crash():
    ppid = os.getppid()
    print(f"pid: {os.getpid()}, ppid: {ppid}", flush=True)
    print(f"Sending SIGTERM to {ppid}", flush=True)
    os.kill(ppid, signal.SIGTERM)
    self = state["SELF_ID"]
    return f"crash {self}!"


# Run in background and maintain the leader election lease
state = run_leader_election()
