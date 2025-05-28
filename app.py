import asyncio
from PIL import Image, ImageDraw
import gradio as gr
from pystray import Icon, MenuItem, Menu
from datetime import datetime
import yaml
import webbrowser
import socket


from config import settings
from config.settings import preferences
from core.copy import LocalRootDirectory, RemoteRootDirectory, SyncDirectory
from backend import get_scheduler


# アイコン用画像作成
def create_icon_image():
    image = Image.new('RGB', (64, 64), 'white')
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill='blue')
    return image


# pystrayタスク（同期関数）
def run_tray():
    def on_exit(icon, item):
        icon.stop()
    def open_console(icon, item):
        url = f"http://127.0.0.1:{preferences.ServerPort}"
        webbrowser.open(url)
        

    icon = Icon(
        'test name',
        icon=create_icon_image(),
        menu=Menu(
            MenuItem('コンソールを開く', open_console),
            MenuItem('終了', on_exit)
        )
    )
    icon.run()


# gradioインターフェースの作成
def create_gradio_ui():
    # リモートフォルダのロック
    def lock_remote(sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
        sync_remote.lock()
        sync_remote.dump()
        root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
        root_remote.dump()
        
    # リモートフォルダのアンロック
    def unlock_remote(sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
        sync_remote.unlock()
        sync_remote.dump()
        root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
        root_remote.dump()


    css = """
#icon, #icon * {
    width: 35px !important;
    font-size: 24px !important;
    line-height: 1.1 !important;
    flex: none !important;
    display: flex;
    align-items: center;
    justify-content: center;
}
"""
    with gr.Blocks(css=css) as demo:
        container = gr.Column()
        gr_timer = gr.Timer(15)
        gr_dummy = gr.State(False)
        gr_state_on = gr.State(False)

        # フォルダ一覧の描画処理
        @gr.render(inputs=[gr_dummy], triggers=[gr_timer.tick, gr_state_on.change])
        def render_items(gr_dummy):
            if gr_dummy:
                return
            # フォルダ一覧取得
            ids: dict[str, dict[str, SyncDirectory]] = {}
            root_local: LocalRootDirectory = yaml.load(settings.local_dump_filename.read_text(encoding='utf8'), Loader=yaml.Loader)
            root_remote: RemoteRootDirectory = yaml.load(settings.remote_dump_filename.read_text(encoding='utf8'), Loader=yaml.Loader)
            gr_state_root_local = gr.State(root_local)
            gr_state_root_remote = gr.State(root_remote)
            for sync_dir in root_local.sync_directories:
                ids[sync_dir.id_] = dict(local=sync_dir)
            for sync_dir in root_remote.sync_directories:
                if sync_dir.id_ not in ids.keys():
                    ids[sync_dir.id_] = dict()
                ids[sync_dir.id_]["remote"] = sync_dir
            # フォルダ概要を表示
            rows = []
            for k, v in ids.items():
                sync_local: SyncDirectory = v["local"] if "local" in v.keys() else None
                sync_remote: SyncDirectory = v["remote"] if "remote" in v.keys() else None
                gr_state_sync_local = gr.State(sync_local)
                gr_state_sync_remote = gr.State(sync_remote)
                with gr.Row(equal_height=True):
                    name = sync_local.path_.stem if sync_local else sync_remote.path_.stem
                    icon_text = "📁\n☁️\n🔒\n"
                    if not sync_local: 
                        icon_text = icon_text.replace("📁", "　")
                    if not sync_remote:
                        icon_text = icon_text.replace("☁️", "　")
                    if not sync_remote or not sync_remote.locked:
                        icon_text = icon_text.replace("🔒", "　")
                    gr_textbox_stem = gr.Textbox(name, label="Name", interactive=False, scale=4)
                    gr_textbox_id = gr.Textbox(k, label="ID", interactive=False, scale=3)
                    gr_textbox_recent_sync = gr.Textbox(sync_remote.recent_sync.strftime("%Y-%m-%d %H:%M:%S"), label="Recent Sync", interactive=False, scale=2)
                    gr_icon = gr.Markdown(icon_text[:-1], elem_id="icon")  # 🔒🔓🔄️▶️⏸️⏹️☁️📁
                    with gr.Column() as lock_col:
                        with gr.Group():
                            gr_button_lock_remote = gr.Button("🔒Lock Remote")
                            gr_button_unlock_remote = gr.Button("🔓Unlock Remote")
                    with gr.Column() as copy_col:
                        with gr.Group():
                            gr_button_remove_local = gr.Button("🗑️Remove local")
                            gr_button_copy_to_local = gr.Button("📥Copy to local")
                    rows.extend([gr_textbox_stem, gr_textbox_id, gr_textbox_recent_sync, gr_icon, lock_col, copy_col])
                    # ボタンクリックイベント登録
                    gr_button_lock_remote.click(lock_remote, inputs=[gr_state_sync_remote, gr_state_root_remote])
                    gr_button_unlock_remote.click(unlock_remote, inputs=[gr_state_sync_remote, gr_state_root_remote])
                    gr_button_remove_local.click()
                    gr_button_copy_to_local.click()
            return rows

        container.render = render_items(gr_dummy)
        demo.load(lambda: True, outputs=gr_state_on)
        return demo


# 非同期のメイン関数
async def main():
    # GradioのUI起動（非ブロッキング）
    demo = create_gradio_ui()
    demo.launch(prevent_thread_lock=True, server_port=preferences.ServerPort)
    # スケジューラ（フォルダ同期処理）起動
    get_scheduler().start()
    # トレイアイコンを非同期スレッドで実行
    await asyncio.to_thread(run_tray)


if __name__ == '__main__':
    asyncio.run(main())
