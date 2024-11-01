from flask import Flask

from .k8s_lease import run_leader_election, load_config

import os, signal

app = Flask(__name__)


@app.route("/")
def index():
    return f"""\
<p>Hello, World!</p>
Leader: {state.current_leader_id}<br>
Self: {state.self_id}<br>
"""


@app.route("/crash", methods=["POST"])
def crash():
    ppid = os.getppid()
    print(f"pid: {os.getpid()}, ppid: {ppid}", flush=True)
    print(f"Sending SIGTERM to {ppid}", flush=True)
    os.kill(ppid, signal.SIGTERM)
    return f"crash {state.self_id}!"


# Run in background and maintain the leader election lease
config = load_config()
state = run_leader_election(config)
