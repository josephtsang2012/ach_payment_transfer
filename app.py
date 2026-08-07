import sys
import traceback
from flask import Flask, jsonify, render_template
from HK_non_trade import main as hk_main

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/run", methods=["POST"])
def run_hk_non_trade():
    try:
        hk_main()
        return jsonify({
            "status": "success", 
            "message": "XML files processed successfully."
        })
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)  # Full traceback for debugging
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

if __name__ == "__main__":
    # For production: consider using waitress or gunicorn later
    app.run(host="0.0.0.0", port=5000, debug=False)
