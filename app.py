import asyncio

from config import settings
from config.settings import preferences
from backend import create_scheduler, start_scheduler
from ui.console import create_gradio_ui
from ui.tray import create_tray_icon


# 非同期のメイン関数
async def main():
    # スケジューラ生成
    create_scheduler()
    # GradioのUI起動（非ブロッキング）
    demo = create_gradio_ui()
    demo.launch(prevent_thread_lock=True, server_port=preferences.ServerPort)
    # スケジューラ起動
    start_scheduler()
    # トレイアイコンを非同期スレッドで実行
    icon = create_tray_icon()
    await asyncio.to_thread(icon.run)


if __name__ == '__main__':
    asyncio.run(main())