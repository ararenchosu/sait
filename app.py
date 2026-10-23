from flask import Flask, render_template, request, jsonify, redirect, make_response
import os
import subprocess
import uuid
import threading
from pathlib import Path

app = Flask(__name__)

def get_password():
    return os.getenv("APP_PASSWORD", "pass123")

def get_secret_key():
    return os.getenv("SECRET_KEY", "dev_fixed_key_20261023")

app.secret_key = get_secret_key()

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR / "workspace"
WORKSPACE.mkdir(exist_ok=True)

running_processes = {}

# ✅ 起動時に自動でパッケージインストール
def install_requirements():
    req_file = WORKSPACE / "requirements.txt"
    if req_file.exists():
        print("📦 必要なパッケージをインストール中...")
        try:
            subprocess.run(
                ["pip3", "install", "-r", str(req_file)],
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ インストール完了")
        except Exception as e:
            print(f"⚠️ インストールエラー: {e}")

# ============================================================
# 🔐 認証
# ============================================================
@app.before_request
def check_auth():
    if request.path in ["/login", "/static"]:
        return
    if not request.cookies.get("dev_auth"):
        return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    
    input_pass = request.form.get("password", "")
    correct_pass = get_password()
    print(f"[DEBUG] 入力: [{input_pass}] / 正: [{correct_pass}]")
    
    if input_pass == correct_pass:
        resp = make_response(redirect("/editor"))
        resp.set_cookie(
            "dev_auth", "ok",
            max_age=86400 * 30,
            samesite="None", secure=True, httponly=True
        )
        print("[DEBUG] ✅ ログイン成功")
        return resp
    
    return render_template("login.html", error="❌ パスワードが違います"), 403

@app.route("/editor")
def editor():
    return render_template("editor.html")

@app.route("/")
def index():
    return redirect("/login")

# ============================================================
# 📁 ファイル管理
# ============================================================
@app.route("/api/files")
def list_files():
    files = []
    for p in WORKSPACE.glob("**/*"):
        if p.is_file():
            files.append({"name": str(p.relative_to(WORKSPACE)), "size": p.stat().st_size})
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
# ▶️ 実行
# ============================================================
@app.route("/api/run", methods=["POST"])
def run_code():
    data = request.json
    filename = data.get("filename", "main.py")
    path = WORKSPACE / filename
    
    print(f"[DEBUG] 実行パス: {path}")
    if not path.exists():
        return jsonify({"error": f"ファイルが見つかりません: {path}"})
    
    session_id = str(uuid.uuid4())
    proc_ref = {"output": [], "exit_code": None}
    
    def task():
        try:
            proc = subprocess.Popen(
                ["python3", str(path)],
                cwd=str(WORKSPACE),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            proc_ref["proc"] = proc
            for line in iter(proc.stdout.readline, ""):
                proc_ref["output"].append(line)
            proc_ref["exit_code"] = proc.wait()
        except Exception as e:
            proc_ref["output"].append(f"エラー: {e}")
            proc_ref["exit_code"] = -1
    
    running_processes[session_id] = proc_ref
    threading.Thread(target=task, daemon=True).start()
    return jsonify({"session_id": session_id})

@app.route("/api/output")
def get_output():
    sid = request.args.get("sid")
    if sid not in running_processes:
        return jsonify({"error": "セッションなし"})
    p = running_processes[sid]
    return jsonify({
        "output": p["output"],
        "running": p["exit_code"] is None,
        "exit_code": p["exit_code"]
    })

@app.route("/api/stop", methods=["POST"])
def stop_process():
    sid = request.json.get("sid")
    if sid in running_processes and "proc" in running_processes[sid]:
        try:
            running_processes[sid]["proc"].terminate()
        except: pass
        running_processes[sid]["exit_code"] = -1
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "ファイルなし"})
    f = request.files["file"]
    path = WORKSPACE / f.filename
    f.save(str(path))
    return jsonify({"success": True, "filename": f.filename})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    pw = get_password()
    print(f"🚀 起動 :{port}")
    print(f"📁 作業フォルダ: {WORKSPACE}")
    print(f"🔐 パスワード: [{pw}]")
    
    # ✅ 初回起動時にdiscord.pyを自動インストール
    install_requirements()
    
    app.run(host="0.0.0.0", port=port, debug=False)
