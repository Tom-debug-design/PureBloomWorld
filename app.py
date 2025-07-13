from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "AtomicBot is running."

@app.route("/heartbeat")
def heartbeat():
    print("💓 Heartbeat triggered (no Discord)")
    return "Heartbeat OK (Flask running via python)"
