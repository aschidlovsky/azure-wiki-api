import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "OK", 200

@app.route("/debug-env")
def debug_env():
    return jsonify({
        "ORG": os.environ.get("AZURE_DEVOPS_ORG"),
        "PROJECT": os.environ.get("AZURE_DEVOPS_PROJECT"),
        "PAT_present": bool(os.environ.get("AZURE_DEVOPS_PAT"))
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

