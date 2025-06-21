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
from typing import Literal, Any, get_type_hints, get_origin, get_args
import re
from itertools import islice
import ulid
import shutil

from config import settings
from config.settings import general_settings
from scripts.custom_script import custom_script_group
from core.dirsync import LocalRootDirectory, RemoteRootDirectory, SyncDirectory
from backend import watch, scheduler
from scripts.custom_script import CustomScript, CustomScriptAttributes
from util.text_util import get_plain_text

# --- コールバック ---

# セッション開始
def start_session():
    return (
        str(general_settings.local_directory),
        str(general_settings.remote_directory),
        general_settings.server_port,
        general_settings.sync_freq_minutes, 
        general_settings.hold_after_modified_days, 
        general_settings.hold_after_created_days, 
        custom_script_group.scripts.copy(),
        datetime.now(),
        datetime.now(),
    )

# ファイル選択
def select_file(default: str, style: int=wx.FD_DEFAULT_STYLE):
    file = default
    dialog = wx.FileDialog(None, "Select File", style=style)
    if dialog.ShowModal() == wx.ID_OK:
        file = dialog.GetPath()
    dialog.Destroy()
    return file

# ディレクトリ選択
def select_directory(default: str, style: int=wx.DD_DEFAULT_STYLE):
    directory = default
    dialog = wx.DirDialog(None, "Select Directory", style=style)
    if dialog.ShowModal() == wx.ID_OK:
        directory = dialog.GetPath()
    dialog.Destroy()
    return directory

# マニュアル同期
def manual_sync():
    if settings.has_root_dirs():
        watch()
    return datetime.now()

# 設定を反映
def apply_settings(local_root: str, remote_root: str, sync_every: int, hold_after_created: int, hold_after_modified: int, port: int):
    general_settings.local_directory = Path(local_root)
    general_settings.remote_directory = Path(remote_root)
    if sync_every != general_settings.sync_freq_minutes:
        general_settings.sync_freq_minutes = sync_every
        scheduler.modify_job(
            job_id="watch_sync",
            trigger=IntervalTrigger(seconds=sync_every*60)
        )
    if hold_after_created != general_settings.hold_after_created_days:
        general_settings.hold_after_created_days = hold_after_created
    if hold_after_modified != general_settings.hold_after_modified_days:
        general_settings.hold_after_modified_days = hold_after_modified
    if port != general_settings.server_port:
        general_settings.server_port = port
    general_settings.dump()
    gr.Info("⚙️ General settings are updated.", title="Settings Saved", duration=settings.gr_info_duration)
    return manual_sync()

# スクリプト辞書作成
def get_script_dicts():
    name_counts: dict[str, int] = {}
    id_name_dict: dict[str, str] = {}
    ids = [Path(x).stem for x in glob("scripts/??????????????????????????/")]
    for id_ in ids:
        name = CustomScriptAttributes.load(id_).name
        suffix = ""
        if name in name_counts.keys():
            suffix = f"({name_counts[name] + 1})"
        else:
            name_counts[name] = 0
        id_name_dict[id_] = name + suffix
        name_counts[name] += 1
    name_id_dict = {v: k for k, v in id_name_dict.items()}
    return id_name_dict, name_id_dict

# 引数オブジェクトの表示
def create_arg_component(annotation: Any, name, script: CustomScript, default: Any):
    """
    annotations: typing.get_type_hints() の戻り値 (引数名 → 型ヒント)
    name: パラメータ名
    param: inspect.signature(...).parameters[name] (inspect.Parameter オブジェクト)

    対応する型ヒントに応じて、適切な Gradio コンポーネントを返す。
    型ヒントとして扱うもの：
      - str
      - int
      - float
      - datetime.datetime
      - list[Any]    （Any は str, int, float, datetime のいずれか）
      - dict[str, Any]
      - Literal[…]
    """
    origin = get_origin(annotation)
    args = get_args(annotation)
    kwargs = {
        "label": name,
        "value": script.kwargs[name] if name in script.kwargs.keys() else default, 
    }

    # 1) Literal の場合
    if origin is Literal:
        # Literal["foo", "bar", ...] のように、args に指定値が入っている
        choices = list(args)
        return gr.Dropdown(
            choices=choices,
            interactive=True,
            **kwargs
        )

    # 2) 単一の型 (origin が None)
    if origin is None:
        # annotation がそのまま型オブジェクトになっているケース
        if annotation is str:
            return gr.Textbox(interactive=True, **kwargs)
        if annotation is Path:
            with gr.Row(equal_height=False, elem_id="row-bottom") as row:
                tb = gr.Textbox(interactive=True, **kwargs, scale=5)
                btn_file = gr.Button("📄 file", elem_id="button-icon")
                btn_dir = gr.Button("📁 directory", elem_id="button-icon")
            btn_file.click(lambda x: select_file(x, wx.FD_DEFAULT_STYLE), inputs=tb, outputs=tb)
            btn_dir.click(lambda x: select_directory(x, wx.DD_DEFAULT_STYLE), inputs=tb, outputs=tb)
            return tb
        if annotation is int:
            # 整数専用なので precision=0
            return gr.Number(precision=0, interactive=True, **kwargs)
        if annotation is float:
            return gr.Number(interactive=True, **kwargs)
        if annotation is datetime:
            return gr.DateTime(interactive=True, **kwargs)
        if annotation is bool:
            return gr.Checkbox(interactive=True, **kwargs)

    # 3) list[...] の場合
    if origin is list:
        # list[Any] を受け取るものとし、Any は str, int, float, datetime のいずれか
        inner_type = args[0] if args else Any
        # 例として「コンマ区切りで入力し、後でパースする」前提の Textbox を返す
        placeholder = f"Enter comma-separated list of {inner_type.__name__}"
        return gr.Textbox(placeholder=placeholder, interactive=True, **kwargs)

    # 4) dict[str, Any] の場合
    if origin is dict:
        key_type, val_type = args if len(args) == 2 else (str, Any)
        # Gradio の JSON コンポーネントを使って辞書を入力させる
        return gr.JSON(interactive=True, **kwargs)

    # 5) その他のケース（未対応）
    raise ValueError(f"Unsupported annotation for '{name}': {annotation!r}")


# カスタムスクリプトの割り当て
def assign_custom_script(name_id_dict: dict[str, str], name: str, idx: int, scripts: list[CustomScript]):
    id_ = name_id_dict[name]
    scripts[idx] = CustomScript.create(id_)
    return (
        scripts,
        idx, 
        datetime.now(),
    )

# カスタムスクリプトの追加
def add_custom_script(scripts: list[CustomScript], id_name_dict: dict[str, str]):
    if len(id_name_dict.keys()) == 0:
        return []
    scripts += [CustomScript.create(tuple(id_name_dict.keys())[0])]
    return scripts, len(scripts) - 1, datetime.now()

# カスタムスクリプトの削除
def remove_custom_script(scripts: list[CustomScript], index_: int):
    script: CustomScript = scripts.pop(index_)
    print(f"Script {index_}[ {script.attributes.name} ] was removed.")
    return scripts, datetime.now()

# カスタムスクリプトの保存
def save_custom_scripts(scripts: list[CustomScript], *args: Any):
    custom_script_group.scripts = scripts.copy()
    args_idx = 0
    for script in scripts:
        script.kwargs = {}
        for name in script.default_values.keys():
            arg = args[args_idx]
            annotation = script.annotations.get(name, str)  # 型ヒント取得
            if get_origin(annotation) is Literal:
                annotation = str
            script.kwargs[name] = annotation(arg)
            args_idx += 1
    custom_script_group.dump()
    gr.Info("🧑‍💻 Custom scripts are updated.", title="Scripts Saved", duration=settings.gr_info_duration)
    return manual_sync()

# カスタムスクリプト生成
def create_new_script(name: str):
    id_ = str(ulid.ULID())
    shutil.copytree(settings.blank_script_path, settings.scripts_path / id_)
    attr = CustomScriptAttributes.load(id_)
    attr.name = name
    attr.dump()
    gr.Info("🥪 New script is created.", title="Script Created", duration=settings.gr_info_duration)
    id_name_dict, name_id_dict = get_script_dicts()
    choices = tuple(id_name_dict.values())
    return id_name_dict, name_id_dict, gr.update(choices=choices, value=choices[-1]), datetime.now()

# カスタムスクリプトプレビュー
def show_script_path(name: str, name_id_dict: dict[str, str]):
    id_ = name_id_dict[name]
    path_text = str((settings.scripts_path / id_).absolute())
    return gr.update(value=path_text)

# 絵文字取得
def get_icon_emojis(sync_rocal: SyncDirectory, sync_remote: SyncDirectory):
    # 🔒🔓🔄️▶️⏸️⏹️☁️📁
    icon_text = "📁\n☁️\n🔒"
    if sync_rocal is None: 
        icon_text = icon_text.replace("📁", "　")
    if sync_remote is None:
        icon_text = icon_text.replace("☁️", "　")
    if sync_remote is None or not sync_remote.is_locked:
        icon_text = icon_text.replace("🔒", "🔄️")
    return icon_text

# リモートディレクトリのロック
def lock_remote(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
    sync_remote.lock()
    sync_remote.dump()
    root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
    root_remote.dump()
    gr.Info(f'🔒 {sync_remote.path_.stem}', title="Locked", duration=settings.gr_info_duration)
    return (
        gr.update(value=get_icon_emojis(sync_local, sync_remote)),
        gr.update(interactive=False), 
        gr.update(interactive=True), 
        gr.update(interactive=sync_local), 
        gr.update(interactive=True), 
    )

# リモートディレクトリのアンロック
def unlock_remote(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_remote: RemoteRootDirectory):
    sync_local_temp = SyncDirectory.create(sync_local.path_)
    sync_remote_temp = SyncDirectory.create(sync_remote.path_)
    sync_remote_temp.is_locked = False
    modified, removed = sync_local_temp.check(sync_remote_temp, mode='synchronizing')
    if len(removed) > 0:
        raise gr.Error(
            "There are files that will be deleted due to sync. Please download the remote directory before unlocking.", 
            title="❗Extra Files Exists", 
            duration=settings.gr_error_duration,
        )
    sync_remote.unlock()
    sync_remote.dump()
    root_remote.sync_directories = [sync_remote if sync_remote.id_ == dir_.id_ else dir_ for dir_ in root_remote.sync_directories]
    root_remote.dump()
    gr.Info(f'🔓 {sync_remote.path_.stem}', title="Unlocked", duration=settings.gr_info_duration)
    return (
        gr.update(value=get_icon_emojis(sync_local, sync_remote)),
        gr.update(interactive=True), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
    )

# ローカルディレクトリの削除
def remove_local_dir(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_local: LocalRootDirectory):
    if not sync_remote.is_locked:
        raise gr.Error("Remote directory is not locked.", title="❗Unlocked Remote", duration=settings.gr_error_duration)
    sync_local.remove()
    root_local.sync_directories = [dir_ for dir_ in root_local.sync_directories if dir_.id_ != sync_local.id_]
    root_local.dump()
    gr.Info(f'🗑️ {sync_local.path_.stem}', title="Removed", duration=settings.gr_info_duration)
    return (
        gr.update(value=get_icon_emojis(None, sync_remote)),
        gr.update(interactive=False), 
        gr.update(interactive=False), 
        gr.update(interactive=False), 
        gr.update(interactive=True), 
    ) 

# リモートディレクトリのダウンロード
def download_remote_dir(sync_local: SyncDirectory, sync_remote: SyncDirectory, root_local: LocalRootDirectory):
    if not sync_remote.is_locked:
        raise gr.Error("Remote directory is not locked.", title="❗Unlocked Remote", duration=settings.gr_error_duration)
    sync_local_temp = None
    sync_remote_temp = SyncDirectory.create(sync_remote.path_)
    if sync_local is None:
        # コピー先ディレクトリ生成
        dst = root_local.path_ / sync_remote.path_.stem
        os.makedirs(dst, exist_ok=True)
        sync_local_temp = SyncDirectory.create(dst, sync_remote.id_)
    else:
        root_local.sync_directories = [dir_ for dir_ in root_local.sync_directories if dir_ != sync_local]
        sync_local_temp = SyncDirectory.create(sync_local.path_)
    # 同期実行
    sync_local_temp.is_locked = False
    sync_remote_temp.sync(sync_local_temp, 'download')
    # ローカルプロパティ更新
    now = sync_remote_temp.synced_at
    sync_local_temp.created_at = sync_remote_temp.created_at
    sync_local_temp.modified_at = now
    sync_local_temp.synced_at = now
    root_local.sync_directories.append(sync_local_temp)
    root_local.dump()
    gr.Info(f'📥 {sync_remote.path_.stem}', title="Downloaded", duration=settings.gr_info_duration)
    return (
        gr.update(value=get_icon_emojis(sync_local_temp, sync_remote_temp)),
        gr.update(interactive=False), 
        gr.update(interactive=True), 
        gr.update(interactive=True), 
        gr.update(interactive=True), 
    ) 

# --- UI実装 ---

# gradioインターフェースの作成
def create_gradio_ui():
    is_initial_call = True
    css = (Path("ui") / "console_main.css").read_text(encoding="utf8")
    with gr.Blocks(css=css) as demo:
        gr_state_refresh_dirs = gr.State(None)
        # 設定
        with gr.Sidebar(width=720, open=not settings.has_root_dirs()):
            gr.Markdown("# Preferences")
            gr.Markdown("## General settings")
            with gr.Row(equal_height=True):
                gr_text_local_root: gr.Textbox = gr.Textbox(label="📁Local Directory", interactive=True)
                gr_btn_open_local: gr.Button = gr.Button("Open", elem_id="button")
            with gr.Row(equal_height=True):
                gr_text_remote_root: gr.Textbox = gr.Textbox(label="☁️Remote Directory", interactive=True)
                gr_btn_open_remote: gr.Button = gr.Button("Open", elem_id="button")
            with gr.Row(equal_height=True):
                gr_num_server_port: gr.Number = gr.Number(
                    minimum=1, step=1, label="💻Console Server Port (from next launch)", interactive=True)
                gr_num_sync_freq_mins: gr.Number = gr.Number(
                    minimum=1, step=1, label="🔄️Sync Every [mins]", interactive=True)
            with gr.Row(equal_height=True):
                gr_num_hold_after_modified_days: gr.Number = gr.Number(
                    minimum=0, step=1, label="📝Remove Local After Modified [days]", interactive=True)
                gr_num_hold_after_created_days: gr.Number = gr.Number(
                    minimum=0, step=1, label="📄Remove Local After Created [days]", interactive=True)
            # 設定ボタン
            gr_btn_apply_settings: gr.Button = gr.Button("Apply", elem_id="button-apply")

            # カスタムスクリプト
            gr.Markdown("## Custom Scripts")
            gr_state_scripts = gr.State(None)
            gr_state_refresh_scripts = gr.State(None)
            gr_state_selected_script = gr.State(None)
            @gr.render(inputs=[gr_state_scripts, gr_state_selected_script], triggers=[gr_state_refresh_scripts.change])
            def render_custom_scripts(scripts: list[CustomScript], selected_script: int):
                # IDと名前の対応表を取得
                id_name_dict, name_id_dict = get_script_dicts()
                gr_state_id_name_dict = gr.State(id_name_dict)
                gr_state_name_id_dict = gr.State(name_id_dict)
                # スクリプト一覧表示
                kwarg_components = []
                for num, script in enumerate(scripts):
                    with gr.Group():
                        gr_dd_script_name = gr.Dropdown(tuple(id_name_dict.values()), value=id_name_dict[script.id_], show_label=False, interactive=True)
                        # docstring
                        with gr.Accordion("💡 Description", open=num == selected_script) as gr_acc_script_description:
                            text = get_plain_text(script.getdoc())
                            gr_md_script_description = gr.Markdown(text)
                        # arguments
                        with gr.Accordion("🧩 Arguments", visible=len(script.default_values) > 0, open=num == selected_script) as gr_acc_script_arguments:
                            for name, default in script.default_values.items():
                                annotation = script.annotations.get(name)
                                kwarg_components.append(create_arg_component(annotation, name, script, default))
                        with gr.Accordion("🗑️ Remove Script", open=False):
                            gr_btn_del_script = gr.Button("Remove", elem_id="button-del")
                    gr_state_script_index = gr.State(num)
                    # イベント
                    gr_dd_script_name.change(
                        assign_custom_script,
                        inputs=[
                            gr_state_name_id_dict, 
                            gr_dd_script_name, 
                            gr_state_script_index, 
                            gr_state_scripts,
                        ],
                        outputs=[
                            gr_state_scripts,
                            gr_state_selected_script, 
                            gr_state_refresh_scripts, 
                        ], 
                        show_progress=False, 
                    )
                    gr_btn_del_script.click(
                        remove_custom_script, 
                        inputs=[gr_state_scripts, gr_state_script_index],
                        outputs=[gr_state_scripts, gr_state_refresh_scripts]
                    )
                gr_btn_add_script.click(
                    add_custom_script, 
                    inputs=[gr_state_scripts, gr_state_id_name_dict],
                    outputs=[gr_state_scripts, gr_state_selected_script, gr_state_refresh_scripts]
                )
                gr_btn_save_scripts.click(
                    save_custom_scripts, 
                    inputs=[gr_state_scripts] + kwarg_components,
                    outputs=gr_state_refresh_dirs
                )
            gr_btn_add_script: gr.Button = gr.Button("Add Script")
            gr_btn_save_scripts: gr.Button = gr.Button("Save Scripts", elem_id="button-apply")

            # スクリプト作成
            gr.Markdown("## Create New Script")
            with gr.Row(equal_height=True):
                gr_tb_script_name: gr.Textbox = gr.Textbox("New Script", show_label=False, interactive=True, scale=2)
                gr_btn_create_script: gr.Button = gr.Button("🥪 Create!")
            # プレビュー
            gr.Markdown("### Script Finder")
            id_name_dict, name_id_dict = get_script_dicts()
            gr_state_id_name_dict: gr.State = gr.State(id_name_dict)
            gr_state_name_id_dict: gr.State = gr.State(name_id_dict)
            with gr.Group():
                gr_dd_preview_script: gr.Dropdown = gr.Dropdown(tuple(id_name_dict.values()), value=None, show_label=False)
                gr_md_script_path: gr.Markdown = gr.Markdown(show_copy_button=True)
            
            # イベント
            gr_btn_open_local.click(lambda x: select_directory(x, wx.DD_DIR_MUST_EXIST), inputs=gr_text_local_root, outputs=gr_text_local_root)
            gr_btn_open_remote.click(lambda x: select_directory(x, wx.DD_DIR_MUST_EXIST), inputs=gr_text_remote_root, outputs=gr_text_remote_root)
            gr_btn_apply_settings.click(apply_settings, inputs=[
                gr_text_local_root,
                gr_text_remote_root,
                gr_num_sync_freq_mins,
                gr_num_hold_after_created_days,
                gr_num_hold_after_modified_days,
                gr_num_server_port,
            ], outputs=gr_state_refresh_dirs)
            gr_btn_create_script.click(
                create_new_script,
                inputs=gr_tb_script_name,
                outputs=[
                    gr_state_id_name_dict,
                    gr_state_name_id_dict,
                    gr_dd_preview_script,
                    gr_state_refresh_scripts
                ]
            )
            gr_dd_preview_script.change(
                show_script_path,
                inputs=[gr_dd_preview_script, gr_state_name_id_dict],
                outputs=gr_md_script_path
            )

        # 同期ボタン
        gr_btn_sync = gr.Button("Sync Manually", elem_id="button-apply")
        gr_btn_sync.click(manual_sync, outputs=gr_state_refresh_dirs)
        # ディレクトリビューワー
        gr_timer = gr.Timer(settings.console_refresh_interval_sec)
        @gr.render(triggers=[gr_timer.tick, gr_state_refresh_dirs.change])
        def render_sync_dirs():
            # ディレクトリ一覧取得
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
            # ディレクトリ概要を表示
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
                            gr_button_lock_remote = gr.Button("🔒Lock Remote", interactive=not sync_remote.is_locked)
                            gr_button_unlock_remote = gr.Button("🔓Unlock Remote", interactive=sync_remote.is_locked and sync_local is not None)
                    with gr.Column() as copy_col:
                        with gr.Group():
                            gr_button_remove_local = gr.Button("🗑️Remove local", interactive=(sync_remote.is_locked and sync_local is not None))
                            gr_button_download_to_local = gr.Button("📥Download to local", interactive=(sync_remote.is_locked))
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
                        gr_button_download_to_local, 
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
                    gr_button_download_to_local.click(
                        download_remote_dir, 
                        inputs=[
                            gr_state_sync_local,
                            gr_state_sync_remote, 
                            gr_state_root_local, 
                        ], 
                        outputs=dir_indicators,
                        show_progress=False, 
                    )
        demo.load(
            start_session, 
            outputs=[
                gr_text_local_root, 
                gr_text_remote_root,
                gr_num_server_port,
                gr_num_sync_freq_mins,
                gr_num_hold_after_modified_days,
                gr_num_hold_after_created_days,
                gr_state_scripts,
                gr_state_refresh_dirs, 
                gr_state_refresh_scripts
            ]
        )
        return demo