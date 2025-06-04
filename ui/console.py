import gradio as gr
import yaml
import wx
app = wx.App(False)
from pathlib import Path
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import os
import inspect
from glob import glob
import html

from config import settings
from config.settings import preferences
from core.dirsync import LocalRootDirectory, RemoteRootDirectory, SyncDirectory
from backend import watch, scheduler
from scripts.custom_script import load_main_function, CustomScriptAttributes

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

# 設定を反映
def apply_settings(local_root: str, remote_root: str, sync_every: int, hold_after_created: int, hold_after_modified: int, port: int):
    preferences.local_directory = Path(local_root)
    preferences.remote_directory = Path(remote_root)
    if sync_every != preferences.sync_freq_minutes:
        preferences.sync_freq_minutes = sync_every
        scheduler.modify_job(
            job_id="watch_sync",
            trigger=IntervalTrigger(seconds=sync_every*60)
        )
    if hold_after_created != preferences.hold_after_created_days:
        preferences.hold_after_created_days = hold_after_created
    if hold_after_modified != preferences.hold_after_modified_days:
        preferences.hold_after_modified_days = hold_after_modified
    if port != preferences.server_port:
        preferences.server_port = port
    preferences.dump()
    gr.Info("Preferences updated.")
    return manual_sync()

# プレーンテキスト取得
def get_plain_text(text):
    text = html.escape(text)
    return f"<pre>{text}</pre>"

# カスタムスクリプトの割り当て
def assign_custom_script(name_id_dict: dict[str, str], name: str, idx: int, script_ids: list[str]):
    id_ = name_id_dict[name]
    fn = load_main_function(id_)
    script_ids[idx] = id_
    description = get_plain_text(f"{inspect.getdoc(fn)}" if inspect.getdoc(fn) else "No Description.")
    return (
        script_ids,
        gr.update(open=True),
        description, 
    )

# カスタムスクリプトの追加
def add_custom_script(script_ids: list[str], id_name_dict: dict[str, str]):
    if len(id_name_dict.keys()) == 0:
        return []
    script_ids += [tuple(id_name_dict.keys())[0]]
    return script_ids, datetime.now()

# カスタムスクリプトの保存
def save_custom_scripts(script_ids: list[str]):
    preferences.custom_scripts = script_ids
    preferences.dump()
    gr.Info("Custom scripts updated.")
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
    is_initial_call = True
    css = (Path("ui") / "console_main.css").read_text(encoding="utf8")
    with gr.Blocks(css=css) as demo:
        gr_state_refresh_dirs = gr.State(False)
        # 設定
        with gr.Sidebar(width=720, open=not settings.has_root_dirs()):
            gr.Markdown("# Preferences")
            gr.Markdown("## Basic settings")
            with gr.Row(equal_height=True):
                gr_text_local: gr.Textbox = gr.Textbox(str(preferences.local_directory), label="📁Local Folder", interactive=False)
                gr_btn_open_local: gr.Button = gr.Button("Open", elem_id="button")
            with gr.Row(equal_height=True):
                gr_text_remote: gr.Textbox = gr.Textbox(str(preferences.remote_directory), label="☁️Remote Folder", interactive=False)
                gr_btn_open_remote: gr.Button = gr.Button("Open", elem_id="button")
            with gr.Row(equal_height=True):
                gr_num_server_port: gr.Number = gr.Number(
                    preferences.server_port, 
                    minimum=1, step=1, label="💻Console Server Port (from next launch)", interactive=True)
                gr_num_sync_freq_mins: gr.Number = gr.Number(
                    preferences.sync_freq_minutes, 
                    minimum=1, step=1, label="🔄️Sync Every [mins]", interactive=True)
            with gr.Row(equal_height=True):
                gr_num_hold_after_modified_days: gr.Number = gr.Number(
                    preferences.hold_after_modified_days, 
                    minimum=0, step=1, label="📝Remove Local After Modified [days]", interactive=True)
                gr_num_hold_after_created_days: gr.Number = gr.Number(
                    preferences.hold_after_created_days, 
                    minimum=0, step=1, label="📄Remove Local After Created [days]", interactive=True)
            # 設定ボタン
            gr_btn_apply_settings: gr.Button = gr.Button("Apply")

            # カスタムスクリプト
            gr.Markdown("## Custom Scripts")
            gr_state_script_ids = gr.State(preferences.custom_scripts.copy())
            gr_state_refresh_scripts = gr.State(False)
            @gr.render(inputs=gr_state_script_ids, triggers=[gr_state_refresh_scripts.change])
            def render_custom_scripts(script_ids: list[str]):
                # IDと名前の対応表を取得
                name_counts: dict[str, int] = {}
                id_name_dict: dict[str, str] = {}
                ids = [Path(x).stem for x in glob("scripts/??????????????????????????/")]
                for id_ in ids:
                    name = CustomScriptAttributes.create(id_).name
                    suffix = ""
                    if name in name_counts.keys():
                        suffix = f"({name_counts[name] + 1})"
                    else:
                        name_counts[name] = 0
                    id_name_dict[id_] = name + suffix
                    name_counts[name] += 1
                name_id_dict = {v: k for k, v in id_name_dict.items()}
                gr_state_id_name_dict = gr.State(id_name_dict)
                gr_state_name_id_dict = gr.State(name_id_dict)
                # スクリプト一覧表示
                for num, id_ in enumerate(script_ids):
                    fn = load_main_function(id_)
                    attr = CustomScriptAttributes.create(id_)
                    with gr.Group():
                        gr_dd_script_name = gr.Dropdown(tuple(id_name_dict.values()), value=id_name_dict[id_], show_label=False, interactive=True)
                        with gr.Accordion("Description", open=False) as gr_acc_script_description:
                            text = get_plain_text(f"{inspect.getdoc(fn)}" if inspect.getdoc(fn) else "No Description.")
                            gr_md_script_description = gr.Markdown(text)
                    gr_state_script_index = gr.State(num)
                    # イベント
                    gr_dd_script_name.change(
                        assign_custom_script,
                        inputs=[
                            gr_state_name_id_dict, 
                            gr_dd_script_name, 
                            gr_state_script_index, 
                            gr_state_script_ids,
                        ],
                        outputs=[
                            gr_state_script_ids,
                            gr_acc_script_description, 
                            gr_md_script_description,
                        ], 
                        show_progress=False, 
                    )
                gr_btn_add_script.click(
                    add_custom_script, 
                    inputs=[gr_state_script_ids, gr_state_id_name_dict],
                    outputs=[gr_state_script_ids, gr_state_refresh_scripts]
                )
                gr_btn_save_scripts.click(
                    save_custom_scripts, 
                    inputs=gr_state_script_ids,
                    outputs=gr_state_refresh_dirs
                )
            gr_btn_add_script: gr.Button = gr.Button("Add Script")
            gr_btn_save_scripts: gr.Button = gr.Button("Save Scripts")
        # イベント
        gr_btn_open_local.click(select_directory, inputs=gr_text_local, outputs=gr_text_local)
        gr_btn_open_remote.click(select_directory, inputs=gr_text_remote, outputs=gr_text_remote)
        gr_btn_apply_settings.click(apply_settings, inputs=[
            gr_text_local,
            gr_text_remote,
            gr_num_sync_freq_mins,
            gr_num_hold_after_created_days,
            gr_num_hold_after_modified_days,
            gr_num_server_port,
        ], outputs=gr_state_refresh_dirs)

        # 同期ボタン
        gr_btn_sync = gr.Button("Sync Manually")
        gr_btn_sync.click(manual_sync, outputs=gr_state_refresh_dirs)
        # フォルダビューワー
        gr_timer = gr.Timer(settings.console_refresh_interval_sec)
        @gr.render(triggers=[gr_timer.tick, gr_state_refresh_dirs.change])
        def render_sync_dirs():
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
        demo.load(lambda: (datetime.now(), datetime.now()), outputs=[gr_state_refresh_dirs, gr_state_refresh_scripts])
        return demo