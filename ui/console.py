import gradio as gr
import yaml
import wx
app = wx.App(False)
from typing import Literal
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from config.settings import preferences
from core.dirsync import LocalRootDirectory, RemoteRootDirectory, SyncDirectory
from backend import watch, scheduler

# --- コールバック ---

# フォルダ選択
def select_directory(default: str):
    folder = default
    dialog = wx.DirDialog(None, "フォルダを選択してください", style=wx.DD_DIR_MUST_EXIST)
    if dialog.ShowModal() == wx.ID_OK:
        folder = dialog.GetPath()
    dialog.Destroy()
    return folder

# フォルダ変更を設定に反映
def change_directory_settings(dir: str, dir_type: Literal["local", "remote"]):
    if dir_type == "local":
        preferences.LocalDirectory = Path(dir)
    if dir_type == "remote":
        preferences.RemoteDirectory = Path(dir)
    preferences.dump()
    if settings.has_root_dirs():
        watch()

# 数値設定を反映
def change_numerical_settings(sync_every: int, hold_after_created: int, hold_after_modified: int, port: int):
    if sync_every != preferences.SyncFreqMinutes:
        preferences.SyncFreqMinutes = sync_every
        scheduler.modify_job(
            job_id="watch_sync",
            trigger=IntervalTrigger(seconds=sync_every*60)
        )
        if settings.has_root_dirs():
            watch()
    if hold_after_created != preferences.HoldAfterCreatedDays:
        preferences.HoldAfterCreatedDays = hold_after_created
    if hold_after_modified != preferences.HoldAfterModifiedDays:
        preferences.HoldAfterModifiedDays = hold_after_modified
    if port != preferences.ServerPort:
        preferences.ServerPort = port
    preferences.dump()
    gr.Info("Setting changed.")

# 絵文字取得
def get_icon_emojis(rocal: bool, remote: bool, locked: bool):
    # 🔒🔓🔄️▶️⏸️⏹️☁️📁
    icon_text = "📁\n☁️\n🔒"
    if not rocal: 
        icon_text = icon_text.replace("📁", "　")
    if not remote:
        icon_text = icon_text.replace("☁️", "　")
    if not locked:
        icon_text = icon_text.replace("🔒", "　")
    return icon_text

# リモートフォルダのロック
def lock_remote(sync_local: LocalRootDirectory, sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
    sync_remote.lock()
    sync_remote.dump()
    root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
    root_remote.dump()
    return (
        gr.update(value=get_icon_emojis(sync_local, sync_remote, True)),
        gr.update(interactive=False), 
        gr.update(interactive=True), 
        gr.update(interactive=True), 
        gr.update(interactive=True), 
    )

# リモートフォルダのアンロック
def unlock_remote(sync_local: LocalRootDirectory, sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
    sync_remote.unlock()
    sync_remote.dump()
    root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
    root_remote.dump()
    return (
        gr.update(value=get_icon_emojis(sync_local, sync_remote, False)),
        gr.update(interactive=True), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
    )

# --- UI実装 ---

# gradioインターフェースの作成
def create_gradio_ui():
    css = (Path("ui") / "console_main.css").read_text(encoding="utf8")
    with gr.Blocks(css=css) as demo:
        # 設定
        has_root_dirs = settings.has_root_dirs()
        with gr.Accordion("Preferences", open=not has_root_dirs) as gr_accordion_pref:
            with gr.Row(equal_height=True):
                gr_text_local: gr.Textbox = gr.Textbox(str(preferences.LocalDirectory), label="📁Local Folder", interactive=False)
                gr_btn_open_local: gr.Button = gr.Button("Open", elem_id="button")
            with gr.Row(equal_height=True):
                gr_text_remote: gr.Textbox = gr.Textbox(str(preferences.RemoteDirectory), label="☁️Remote Folder", interactive=False)
                gr_btn_open_remote: gr.Button = gr.Button("Open", elem_id="button")
            with gr.Row(equal_height=True):
                gr_num_sync_freq_mins: gr.Number = gr.Number(preferences.SyncFreqMinutes, minimum=1, step=1, label="🔄️Sync Every [mins]", interactive=True)
                gr_num_hold_after_created_days: gr.Number = gr.Number(preferences.HoldAfterCreatedDays, minimum=1, step=1, label="📄Remove Local After Created [days]", interactive=True)
                gr_num_hold_after_modified_days: gr.Number = gr.Number(preferences.HoldAfterModifiedDays, minimum=1, step=1, label="📝Remove Local After Modified [days]", interactive=True)
                gr_num_server_port: gr.Number = gr.Number(preferences.ServerPort, minimum=1, step=1, label="💻Console Server Port (from next launch)", interactive=True)
                gr_btn_apply_settings: gr.Button = gr.Button("Apply", elem_id="button")
        gr_btn_open_local.click(select_directory, inputs=gr_text_local, outputs=gr_text_local)
        gr_btn_open_remote.click(select_directory, inputs=gr_text_remote, outputs=gr_text_remote)
        gr_text_local.change(change_directory_settings, inputs=[gr_text_local, gr.State("local")])
        gr_text_remote.change(change_directory_settings, inputs=[gr_text_remote, gr.State("remote")])
        gr_btn_apply_settings.click(change_numerical_settings, inputs=[
            gr_num_sync_freq_mins,
            gr_num_hold_after_created_days,
            gr_num_hold_after_modified_days,
            gr_num_server_port,
        ])
        # フォルダビューワー
        container = gr.Column()
        gr_timer = gr.Timer(settings.console_refresh_interval_sec)
        gr_dummy = gr.State(False)
        gr_state_on = gr.State(False)

        # フォルダ一覧の描画処理
        @gr.render(inputs=[gr_dummy], triggers=[gr_timer.tick, gr_state_on.change])
        def render_items(gr_dummy):
            if gr_dummy:
                return
            # フォルダ一覧取得
            if not settings.local_dump_filename.exists() or not settings.remote_dump_filename.exists():
                return
            root_local: LocalRootDirectory = yaml.load(settings.local_dump_filename.read_text(encoding='utf8'), Loader=yaml.Loader)
            root_remote: RemoteRootDirectory = yaml.load(settings.remote_dump_filename.read_text(encoding='utf8'), Loader=yaml.Loader)
            ids: dict[str, dict[str, SyncDirectory]] = {}
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
                sync_local: SyncDirectory = v["local"] if "local" in v.keys() else False
                sync_remote: SyncDirectory = v["remote"] if "remote" in v.keys() else False
                gr_state_sync_local = gr.State(sync_local)
                gr_state_sync_remote = gr.State(sync_remote)
                with gr.Row(equal_height=True):
                    name = sync_local.path_.stem if sync_local else sync_remote.path_.stem
                    gr_textbox_stem = gr.Textbox(name, label="Name", interactive=False, scale=4)
                    gr_textbox_id = gr.Textbox(k, label="ID", interactive=False, scale=3)
                    gr_textbox_recent_sync = gr.Textbox(sync_remote.recent_sync.strftime("%Y-%m-%d %H:%M:%S"), label="Recent Sync", interactive=False, scale=2)
                    locked = sync_remote.locked if sync_remote else False
                    gr_md_icon = gr.Markdown(get_icon_emojis(sync_local, sync_remote, locked), elem_id="icon")
                    with gr.Column() as lock_col:
                        with gr.Group():
                            gr_button_lock_remote = gr.Button("🔒Lock Remote", interactive=not sync_remote.locked)
                            gr_button_unlock_remote = gr.Button("🔓Unlock Remote", interactive=sync_remote.locked)
                    with gr.Column() as copy_col:
                        with gr.Group():
                            gr_button_remove_local = gr.Button("🗑️Remove local", interactive=sync_remote.locked)
                            gr_button_copy_to_local = gr.Button("📥Copy to local", interactive=sync_remote.locked)
                    rows.extend([gr_textbox_stem, gr_textbox_id, gr_textbox_recent_sync, gr_md_icon, lock_col, copy_col])
                    # ボタンクリックイベント登録
                    gr_button_lock_remote.click(
                        lock_remote, 
                        inputs=[
                            gr_state_sync_local,
                            gr_state_sync_remote, 
                            gr_state_root_remote
                        ], 
                        outputs=[
                            gr_md_icon,
                            gr_button_lock_remote, 
                            gr_button_unlock_remote, 
                            gr_button_remove_local, 
                            gr_button_copy_to_local, 
                        ],
                        show_progress=False, 
                    )
                    gr_button_unlock_remote.click(
                        unlock_remote, 
                        inputs=[
                            gr_state_sync_local,
                            gr_state_sync_remote, 
                            gr_state_root_remote
                        ], 
                        outputs=[
                            gr_md_icon,
                            gr_button_lock_remote, 
                            gr_button_unlock_remote, 
                            gr_button_remove_local, 
                            gr_button_copy_to_local, 
                        ],
                        show_progress=False, 
                    )
                    gr_button_remove_local.click()
                    gr_button_copy_to_local.click()
            return rows

        container.render = render_items(gr_dummy)
        demo.load(lambda: True, outputs=gr_state_on)
        return demo