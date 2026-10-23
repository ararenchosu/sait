import discord
from discord.ext import commands
import asyncio
import os
import threading
from flask import Flask, render_template, request, jsonify

# ============================================================
# Discord Bot 本体
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.is_running = False
        self.start_time = None

    async def setup_hook(self):
        print("🔧 Botセットアップ中...")
        if os.path.exists("./cogs"):
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and not filename.startswith("_"):
                    try:
                        await self.load_extension(f"cogs.{filename[:-3]}")
                        print(f"✅ Cog: {filename[:-3]}")
                    except Exception as e:
                        print(f"⚠️ {filename}: {e}")
        synced = await self.tree.sync()
        print(f"✅ コマンド同期: {len(synced)}件")

    async def on_ready(self):
        self.is_running = True
        from datetime import datetime
        self.start_time = datetime.now()
        print(f"✅ Botログイン: {self.user}")

bot = MyBot()
bot_loop = None
bot_thread = None

# ============================================================
# ウェブ管理サイト
# ============================================================
web_app = Flask(__name__)
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "admin123")  # 管理画面のパスワード

@web_app.before_request
def check_auth():
    if request.path in ["/login", "/static"]:
        return
    if not request.cookies.get("authorized"):
        return render_template("login.html")

@web_app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == WEB_PASSWORD:
            resp = render_template("index.html")
            resp.set_cookie("authorized", "yes", max_age=86400)
            return resp
        return "❌ パスワードが違います"
    return render_template("login.html")

@web_app.route("/")
def index():
    return render_template("index.html")

@web_app.route("/api/status")
def status():
    running = bot.is_running
    uptime = None
    if running and bot.start_time:
        from datetime import datetime
        delta = datetime.now() - bot.start_time
        uptime = str(delta).split(".")[0]
    return jsonify({
        "running": running,
        "user": str(bot.user) if running else None,
        "guilds": len(bot.guilds) if running else 0,
        "uptime": uptime
    })

@web_app.route("/api/start", methods=["POST"])
def start_bot():
    global bot_loop, bot_thread
    if bot.is_running:
        return jsonify({"success": False, "error": "すでに起動しています"})
    
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        return jsonify({"success": False, "error": "トークンが設定されていません"})
    
    def run_bot():
        global bot_loop
        bot_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(bot_loop)
        bot_loop.run_until_complete(bot.start(token))
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return jsonify({"success": True, "message": "Botを起動しました"})

@web_app.route("/api/stop", methods=["POST"])
def stop_bot():
    if not bot.is_running:
        return jsonify({"success": False, "error": "起動していません"})
    
    async def close_bot():
        await bot.close()
    
    if bot_loop:
        asyncio.run_coroutine_threadsafe(close_bot(), bot_loop)
    return jsonify({"success": True, "message": "Botを停止しました"})

# ============================================================
# 起動
# ============================================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"🌐 管理サイト起動 :{port}")
    print("🔐 管理画面パスワード:", WEB_PASSWORD)
    web_app.run(host="0.0.0.0", port=port, debug=False)
