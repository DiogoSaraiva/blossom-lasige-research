from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/position", methods=["POST"])
def receive_position():
    data = request.json
    print(f"[DummyBlossom] Received payload: {data}")
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("[DummyBlossom] Server running at http://localhost:8000")
    app.run(host="0.0.0.0", port=8000)