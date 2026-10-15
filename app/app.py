import os, random
from flask import Flask, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
VERSION = os.getenv("VERSION", "v1")
ERROR_RATE = float(os.getenv("ERROR_RATE", "0"))
REQS = Counter("http_requests_total", "Requests", ["status", "version"])

@app.route("/")
def home():
    if random.random() < ERROR_RATE:
        REQS.labels("500", VERSION).inc()
        return "error", 500
    REQS.labels("200", VERSION).inc()
    return f"Hello from {VERSION}\n"

@app.route("/health")
def health():
    return "ok"

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)

app.run(host="0.0.0.0", port=8080)