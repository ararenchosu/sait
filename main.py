import discord
from discord.ext import commands
import asyncio
import os
import threading
from dotenv import load_dotenv

# ✅ 外部ファイル（.env）から設定を読み込み
load_dotenv()

# ============================================================
# Intents 設定
# ============================================================
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
        flask_app.run(
            host="0.0.0.0",
            port=int(os.getenv("WEB_PORT", 8080)),
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        print(f"⚠️ ウェブサーバー: {e}")

# ============================================================
# メイン実行
# ============================================================
async def main():
    # ✅ ウェブサーバーを別スレッドで起動
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    print(f"✅ ウェブサーバー起動 — ポート {os.getenv('WEB_PORT', 8080)}")

    # ✅ トークン取得（外部.envから）
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ エラー: .env に DISCORD_TOKEN を設定してください")
        print("   例: DISCORD_TOKEN=xxxxxxxxxxx")
        return

    # ✅ Bot起動
    await bot.start(token)

bot = MyBot()

if __name__ == "__main__":
    asyncio.run(main())
