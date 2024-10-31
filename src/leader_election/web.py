from flask import Flask
import os

app = Flask(__name__)


@app.route("/")
def index():
    return "<p>Hello, World!</p>"


@app.route("/crash", methods=["POST"])
def crash():
    # TODO: crash granian process
    os.kill(1, 9)
    return "crash"


# TODO: run run_leader_election in a thread, use shared state
