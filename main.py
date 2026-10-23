import discord
from discord.ext import commands
import asyncio
import os
import threading

# ✅ FadeHostの環境変数を直接読み込む
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# ============================================================
# Bot 本体
# ============================================================
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        print("🔧 セットアップ開始")
        
        # ✅ Cog自動読み込み
        if os.path.exists("./cogs"):
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and not filename.startswith("_"):
                    try:
                        await self.load_extension(f"cogs.{filename[:-3]}")
                        print(f"✅ Cog: {filename[:-3]}")
                    except Exception as e:
                        print(f"⚠️ {filename} 読み込み失敗: {e}")
        
        # ✅ コマンド同期
        synced = await self.tree.sync()
        print(f"✅ コマンド同期: {len(synced)}件")

    async def on_ready(self):
        print(f"✅ ログイン完了: {self.user}")
        print(f"✅ 稼働中 — 全サーバー: {len(self.guilds)}基")

# ============================================================
# ウェブサーバー起動
# ============================================================
def run_web():
    try:
        from web.app import app as flask_app
        port = int(os.getenv("WEB_PORT", 8080))
        flask_app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        print(f"⚠️ ウェブサーバー: {e}")

# ============================================================
# メイン実行
# ============================================================
async def main():
    # ✅ ウェブサーバー起動
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    port = int(os.getenv("WEB_PORT", 8080))
    print(f"✅ ウェブサーバー起動 — ポート {port}")

    # ✅ FadeHostの環境変数からトークン取得
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ エラー: FadeHostの環境変数に DISCORD_TOKEN を設定してください")
        return

    await bot.start(token)

bot = MyBot()

if __name__ == "__main__":
    asyncio.run(main())
