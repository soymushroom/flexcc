import gradio as gr
import yaml
import wx
app = wx.App(False)
from pathlib import Path
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import os

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

# マニュアル同期
def manual_sync():
    if settings.has_root_dirs():
        watch()
    return datetime.now()

# 数値設定を反映
def apply_settings(local_root: str, remote_root: str, sync_every: int, hold_after_created: int, hold_after_modified: int, port: int):
    preferences.LocalDirectory = Path(local_root)
    preferences.RemoteDirectory = Path(remote_root)
    if sync_every != preferences.SyncFreqMinutes:
        preferences.SyncFreqMinutes = sync_every
        scheduler.modify_job(
            job_id="watch_sync",
            trigger=IntervalTrigger(seconds=sync_every*60)
        )
    if hold_after_created != preferences.HoldAfterCreatedDays:
        preferences.HoldAfterCreatedDays = hold_after_created
    if hold_after_modified != preferences.HoldAfterModifiedDays:
        preferences.HoldAfterModifiedDays = hold_after_modified
    if port != preferences.ServerPort:
        preferences.ServerPort = port
    preferences.dump()
    gr.Info("Preferences updated.")
    return manual_sync()

# 絵文字取得
def get_icon_emojis(sync_rocal: SyncDirectory, sync_remote: SyncDirectory):
    # 🔒🔓🔄️▶️⏸️⏹️☁️📁
    icon_text = "📁\n☁️\n🔒"
    if sync_rocal is None: 
        icon_text = icon_text.replace("📁", "　")
    if sync_remote is None:
        icon_text = icon_text.replace("☁️", "　")
    if sync_remote is None or not sync_remote.locked:
        icon_text = icon_text.replace("🔒", "🔄️")
    return icon_text

# リモートフォルダのロック
def lock_remote(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
    sync_remote.lock()
    sync_remote.dump()
    root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
    root_remote.dump()
    return (
        gr.update(value=get_icon_emojis(sync_local, sync_remote)),
        gr.update(interactive=False), 
        gr.update(interactive=True), 
        gr.update(interactive=sync_local), 
        gr.update(interactive=not sync_local), 
    )

# リモートフォルダのアンロック
def unlock_remote(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
    sync_remote.unlock()
    sync_remote.dump()
    root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
    root_remote.dump()
    return (
        gr.update(value=get_icon_emojis(sync_local, sync_remote)),
        gr.update(interactive=True), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
    )

# ローカルフォルダの削除
def remove_local_dir(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_local: LocalRootDirectory):
    if not sync_remote.locked:
        raise gr.Error("Remote folder is not locked.")
    sync_local.remove()
    root_local.sync_directories = [dir_ for dir_ in root_local.sync_directories if dir_.id_ != sync_local.id_]
    root_local.dump()
    return (
        get_icon_emojis(None, sync_remote),
        gr.update(interactive=False), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
        gr.update(interactive=True), 
    ) 

# リモートフォルダのダウンロード
def download_remote_dir(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_local: LocalRootDirectory):
    if not sync_remote.locked:
        raise gr.Error("Remote folder is not locked.")
    if sync_local is not None:
        raise gr.Error("Local folder already exists.")
    # コピー先フォルダ生成
    dst = root_local.path_ / sync_remote.path_.stem
    os.makedirs(dst, exist_ok=True)
    sync_local = SyncDirectory.create(dst, sync_remote.id_)
    # 同期実行
    sync_remote.sync(sync_local)
    # ローカルプロパティ更新
    now = sync_remote.synced_at
    sync_local.created_at = sync_remote.created_at
    sync_local.modified_at = now
    sync_local.synced_at = now
    root_local.sync_directories.append(sync_local)
    root_local.dump()
    return (
        get_icon_emojis(sync_local, sync_remote),
        gr.update(interactive=False), 
        gr.update(interactive=True), 
        gr.update(interactive=True), 
        gr.update(interactive=False), 
    ) 

# --- UI実装 ---

# gradioインターフェースの作成
def create_gradio_ui():
    css = (Path("ui") / "console_main.css").read_text(encoding="utf8")
    with gr.Blocks(css=css) as demo:
        gr_state_on = gr.State(False)
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
                gr_num_hold_after_created_days: gr.Number = gr.Number(preferences.HoldAfterCreatedDays, minimum=0, step=1, label="📄Remove Local After Created [days]", interactive=True)
                gr_num_hold_after_modified_days: gr.Number = gr.Number(preferences.HoldAfterModifiedDays, minimum=0, step=1, label="📝Remove Local After Modified [days]", interactive=True)
                gr_num_server_port: gr.Number = gr.Number(preferences.ServerPort, minimum=1, step=1, label="💻Console Server Port (from next launch)", interactive=True)
            gr_btn_apply_settings: gr.Button = gr.Button("Apply")
        gr_btn_open_local.click(select_directory, inputs=gr_text_local, outputs=gr_text_local)
        gr_btn_open_remote.click(select_directory, inputs=gr_text_remote, outputs=gr_text_remote)
        gr_btn_apply_settings.click(apply_settings, inputs=[
            gr_text_local,
            gr_text_remote,
            gr_num_sync_freq_mins,
            gr_num_hold_after_created_days,
            gr_num_hold_after_modified_days,
            gr_num_server_port,
        ], outputs=gr_state_on)
        # 同期ボタン
        gr_btn_sync = gr.Button("Sync Manually")
        gr_btn_sync.click(manual_sync, outputs=gr_state_on)
        # フォルダビューワー
        container = gr.Column()
        gr_timer = gr.Timer(settings.console_refresh_interval_sec)
        gr_dummy = gr.State(False)

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
            # 同期時刻を表示
            synced_at = ""
            sync_times = [x.synced_at for x in root_local.sync_directories]
            if sync_times:
                synced_at = max(sync_times).strftime("%Y-%m-%d %H:%M")
            gr.Markdown(f"Synced at: {synced_at}")
            # フォルダ概要を表示
            rows = []
            for k, v in sorted(ids.items(), reverse=True):
                sync_local: SyncDirectory = v["local"] if "local" in v.keys() else None
                sync_remote: SyncDirectory = v["remote"] if "remote" in v.keys() else None
                gr_state_sync_local = gr.State(sync_local)
                gr_state_sync_remote = gr.State(sync_remote)
                with gr.Row(equal_height=True):
                    name = sync_local.path_.stem if sync_local else sync_remote.path_.stem
                    gr_textbox_stem = gr.Textbox(name, label="Name", interactive=False, scale=4)
                    gr_textbox_created_at = gr.Textbox(
                        sync_remote.created_at.strftime("%Y-%m-%d %H:%M"), 
                        label="📄Created at", interactive=False, scale=1
                    )
                    modified_at = sync_local.modified_at if sync_local is not None else sync_remote.modified_at
                    gr_textbox_modified_at = gr.Textbox(
                        modified_at.strftime("%Y-%m-%d %H:%M"), 
                        label="📝Modified at", interactive=False, scale=1
                    )
                    gr_textbox_be_removed_at = gr.Textbox(
                        sync_local.be_removed_at.strftime("%Y-%m-%d %H:%M") if sync_local is not None else "", 
                        label="🗑️Remove local at", interactive=False, scale=1
                    )
                    gr_md_icon = gr.Markdown(get_icon_emojis(sync_local, sync_remote), elem_id="icon")
                    with gr.Column() as lock_col:
                        with gr.Group():
                            gr_button_lock_remote = gr.Button("🔒Lock Remote", interactive=not sync_remote.locked)
                            gr_button_unlock_remote = gr.Button("🔓Unlock Remote", interactive=sync_remote.locked and sync_local is not None)
                    with gr.Column() as copy_col:
                        with gr.Group():
                            gr_button_remove_local = gr.Button("🗑️Remove local", interactive=(sync_remote.locked and sync_local is not None))
                            gr_button_copy_to_local = gr.Button("📥Copy to local", interactive=(sync_remote.locked and sync_local is None))
                    rows.extend([
                        gr_textbox_stem, 
                        gr_textbox_created_at, 
                        gr_textbox_modified_at, 
                        gr_textbox_be_removed_at, 
                        gr_md_icon, 
                        lock_col, 
                        copy_col,
                    ])
                    # ボタンクリックイベント登録
                    dir_indicators = [
                        gr_md_icon,
                        gr_button_lock_remote, 
                        gr_button_unlock_remote, 
                        gr_button_remove_local, 
                        gr_button_copy_to_local, 
                    ]
                    gr_button_lock_remote.click(
                        lock_remote, 
                        inputs=[
                            gr_state_sync_local,
                            gr_state_sync_remote, 
                            gr_state_root_remote
                        ], 
                        outputs=dir_indicators,
                        show_progress=False, 
                    )
                    gr_button_unlock_remote.click(
                        unlock_remote, 
                        inputs=[
                            gr_state_sync_local,
                            gr_state_sync_remote, 
                            gr_state_root_remote
                        ], 
                        outputs=dir_indicators,
                        show_progress=False, 
                    )
                    gr_button_remove_local.click(
                        remove_local_dir, 
                        inputs=[
                            gr_state_sync_local,
                            gr_state_sync_remote, 
                            gr_state_root_local, 
                        ], 
                        outputs=dir_indicators,
                        show_progress=False, 
                    )
                    gr_button_copy_to_local.click(
                        download_remote_dir, 
                        inputs=[
                            gr_state_sync_local,
                            gr_state_sync_remote, 
                            gr_state_root_local, 
                        ], 
                        outputs=dir_indicators,
                        show_progress=False, 
                    )
            return rows

        container.render = render_items(gr_dummy)
        demo.load(lambda: True, outputs=gr_state_on)
        return demo