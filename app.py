from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import subprocess
import uuid
import threading
import time
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_env_key_change_me")
APP_PASSWORD = os.getenv("APP_PASSWORD", "pass123")

# 作業フォルダ
WORKSPACE = Path("./workspace")
WORKSPACE.mkdir(exist_ok=True)

# 実行中プロセス管理
running_processes = {}

# ============================================================
# 🔐 認証
# ============================================================
@app.before_request
def auth():
    if request.path in ["/login", "/static"]:
        return
    if not request.cookies.get("dev_auth"):
        return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            resp = render_template("editor.html")
            resp.set_cookie("dev_auth", "ok", max_age=86400*30)
            return resp
        return "❌ パスワードが違います"
    return render_template("login.html")

# ============================================================
# 🖥️ ページ
# ============================================================
@app.route("/")
def index():
    return render_template("editor.html")

# ============================================================
# 📁 ファイル管理API
# ============================================================
@app.route("/api/files")
def list_files():
    files = []
    for p in WORKSPACE.glob("**/*"):
        if p.is_file():
            files.append({
                "name": str(p.relative_to(WORKSPACE)),
                "size": p.stat().st_size
            })
    return jsonify({"files": files})

@app.route("/api/file/save", methods=["POST"])
def save_file():
    data = request.json
    path = WORKSPACE / data["filename"]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data["code"], encoding="utf-8")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/file/read", methods=["POST"])
def read_file():
    data = request.json
    path = WORKSPACE / data["filename"]
    if not path.exists():
        return jsonify({"error": "ファイルが存在しません"})
    return jsonify({"code": path.read_text(encoding="utf-8")})

@app.route("/api/file/delete", methods=["POST"])
def delete_file():
    data = request.json
    path = WORKSPACE / data["filename"]
    if path.exists():
        path.unlink()
        return jsonify({"success": True})
    return jsonify({"success": False})

# ============================================================
# ▶️ 実行・ターミナルAPI
# ============================================================
@app.route("/api/run", methods=["POST"])
def run_code():
    data = request.json
    filename = data.get("filename", "main.py")
    path = WORKSPACE / filename
    
    if not path.exists():
        return jsonify({"error": "ファイルが見つかりません"})
    
    session_id = str(uuid.uuid4())
    
    def execute():
        try:
            proc = subprocess.Popen(
                ["python3", str(path)],
                cwd=str(WORKSPACE),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            running_processes[session_id] = proc
            
            for line in iter(proc.stdout.readline, ""):
                if session_id in running_processes:
                    running_processes[session_id]["output"].append(line)
            
            ret = proc.wait()
            if session_id in running_processes:
                running_processes[session_id]["exit_code"] = ret
        except Exception as e:
            if session_id in running_processes:
                running_processes[session_id]["output"].append(f"エラー: {e}")
    
    running_processes[session_id] = {
        "output": [],
        "exit_code": None,
        "thread": threading.Thread(target=execute, daemon=True)
    }
    running_processes[session_id]["thread"].start()
    
    return jsonify({"session_id": session_id})

@app.route("/api/output")
def get_output():
    sid = request.args.get("sid")
    if sid not in running_processes:
        return jsonify({"error": "セッションが存在しません"})
    
    proc = running_processes[sid]
    return jsonify({
        "output": proc["output"],
        "running": proc["exit_code"] is None,
        "exit_code": proc["exit_code"]
    })

@app.route("/api/stop", methods=["POST"])
def stop_process():
    data = request.json
    sid = data.get("sid")
    if sid in running_processes:
        proc = running_processes[sid]
        if isinstance(proc, dict) and hasattr(proc, "kill"):
            proc.kill()
        running_processes[sid]["exit_code"] = -1
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "ファイルがありません"})
    f = request.files["file"]
    path = WORKSPACE / f.filename
    f.save(str(path))
    return jsonify({"success": True, "filename": f.filename})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 開発環境起動 :{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
