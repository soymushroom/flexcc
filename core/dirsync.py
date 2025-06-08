from __future__ import annotations
from pydantic import BaseModel, field_validator
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, time
import ulid
from pathlib import Path
from glob import glob
import yaml
import os
import subprocess
import shutil
import ctypes
from win11toast import toast
import io
from contextlib import redirect_stdout
import copy
import inspect
import re

from config import settings
from config.settings import general_settings
from util.text_util import enable_hide_tag
from util.path_util import is_subpath


class SyncDirectory(BaseModel):
    """
    同期対象のフォルダ状態を保持するクラス
    """

    path_: Path
    id_: str
    created_at: datetime = datetime.now()
    modified_at: datetime = created_at
    synced_at: datetime = created_at
    modify_log: str = ''
    locked: bool = False
    @property
    def be_removed_at(self) -> datetime:
        created_at = datetime.combine(self.created_at.date(), time.min)
        modified_at = datetime.combine(self.modified_at.date(), time.min)
        after_create = created_at + timedelta(days=general_settings.hold_after_created_days)
        after_modify = modified_at + timedelta(days=general_settings.hold_after_modified_days)
        removed_at = max(after_create, after_modify) + timedelta(days=1)
        return removed_at


    def copy(self):
        return copy.copy(self)

    def dump(self) -> str:
        filename = self.path_ / settings.sync_dir_ext
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filename))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(filename), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        filename.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')

    def sync(self, dst: SyncDirectory):
        from scripts.custom_script import CustomScript, custom_script_group
        now = datetime.now()
        logs: list[str] = []
        if dst.locked:
            # ロックされているフォルダなら中断
            print(f'\nLocked Remote: {dst.path_.stem}\nSync skipped')
            return
        # 初期化
        self.synced_at = now
        command: list = [
            "robocopy",
            self.path_,
            dst.path_,
            "/MIR",   # ミラーリング
            "/L",     # 実行せずに出力だけ
            "/NP",    # 進行状況バー非表示
            "/NDL",   # ディレクトリ一覧非表示
            "/NS",    # ファイルサイズを表示しない
            "/NC",    # クラス（例：新規ファイルなど）を表示しない
            "/NJH",   # ジョブヘッダを表示しない（開始時の情報）
            "/NJS",   # ジョブサマリを表示しない（統計情報）
        ]
        print(f'\nSync: {self.path_.stem}')
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        sync_log = None
        do_rename = dst.path_.stem != self.path_.stem  # リネーム実行要否
        do_sync = False  # 同期実行要否
        # 同期実行可否チェック
        modified_files, removed_files = [], []
        if result.returncode > 7:
            print('Error')
        elif result.returncode == 0:
            print('No change')
        elif result.returncode:
            do_sync = True
            # ファイル一覧取得
            sync_log = result.stdout[1:-1].replace('\t', '')
            print("Files will be synced: ")
            print(sync_log)
            pattern = re.compile(r" *(.*)")
            paths = [Path(pattern.match(x).group(1)) for x in sync_log.split("\n")]
            # 編集対象か削除対象かを判定（リモート配下のファイルなら削除対象）
            for path_ in paths:
                if is_subpath(self.path_, path_):
                    modified_files.append(path_.relative_to(self.path_))
                else:
                    removed_files.append(path_.relative_to(dst.path_))
        # カスタムスクリプト実行
        if do_rename or do_sync:
            for script in custom_script_group.scripts:
                print(f"Run custom script: {script.attributes.name}")
                print("--- docstring ---")
                print(enable_hide_tag(script.getdoc()))
                print("--- run ---")
                script.run(self, dst, modified_files, removed_files)
                print("--- end ---")
        # ローカルに合わせてリモートフォルダをリネーム
        dst_path = dst.path_
        if do_rename:
            dst_path = dst.path_.parent / self.path_.stem
            os.rename(dst.path_, dst_path)
            log = f'Rename remote: \n{dst.path_} \n > {dst_path}'
            print(f'\n{log}')
            logs.append(log)
            self.modified_at = now
        # ミラーリング実行
        if do_sync:
            command[2] = dst_path  # 同期先を更新（リネーム対応）
            command = [c for c in command if c != '/L']
            print("Sync Start")
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            sync_log = result.stdout[1:-1].replace('\t', '')
            print(f"Completed: Synced {len(sync_log.split("\n"))} files")
            # 結果更新
            logs.append(f'Sync: {self.path_.stem}\n{sync_log}')
            self.modified_at = now
        else:
            print('Not synced')
        # 同期ログ出力
        if logs:
            self.modify_log = '\n\n'.join(logs)
        self.dump()
        shutil.copy2(self.path_ / settings.sync_dir_ext, dst_path / settings.sync_dir_ext)
        sync_remote = SyncDirectory.create(dst_path)
        # 削除チェック
        print(f'Local will be removed at: {self.be_removed_at:%Y-%m-%d %H:%M}')
        if (now > self.be_removed_at):
            # リモートをロックして自身を削除
            sync_remote.locked = True
            sync_remote.dump()
            self.remove()
            print(f"Remove local: {self.path_.stem}")
        return sync_remote
    
    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

    def remove(self):
        shutil.rmtree(self.path_)
    
    def download(self, root_local: LocalRootDirectory):
        shutil.copy(self.path_, root_local.path_ / self.path_)

    
    @classmethod
    def create(cls, path_: Path, anew_id: str=None) -> 'SyncDirectory':
        if not path_.exists():
            os.makedirs(path_)
        filename = path_ / settings.sync_dir_ext
        if filename.exists():
            if anew_id:
                # フォルダ生成先がすでに存在する
                raise FileExistsError()
            instance: SyncDirectory = yaml.load(filename.read_text(encoding='utf8'), Loader=yaml.Loader)
            instance.path_ = path_
        else:
            if not anew_id:
                anew_id = str(ulid.ULID())
            instance = cls(path_=path_, id_=anew_id)
            filename.write_text(yaml.dump(instance, allow_unicode=True), encoding='utf8')
        return instance


class RootDirectory(BaseModel, ABC):
    """
    ローカルまたはリモートフォルダの状態を保持するクラス
    """

    path_: Path | None
    sync_directories: list[SyncDirectory] = []


    def check(self):
        dirs = [Path(p) for p in glob(str(self.path_ / '*') + '\\')]
        for dir in dirs:
            sdir = SyncDirectory.create(path_=dir)
            self.sync_directories.append(sdir)
            print(f'{dir.stem}: {sdir.id_}')
    

    def dump(self, filename: Path) -> str:
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filename))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(filename), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        filename.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')


class LocalRootDirectory(RootDirectory):
    """
    ローカルフォルダ
    """


    def dump(self):
        return super().dump(settings.local_dump_filename)
    

    def sync(self, remote_root: RemoteRootDirectory):
        # フォルダのリネーム
        local_dir_dict: dict[str, SyncDirectory] = {d.id_: d for d in self.sync_directories}
        remote_dir_dict: dict[str, SyncDirectory] = {d.id_: d for d in remote_root.sync_directories}
        # ローカルとリモートのペアを作成
        local_dir: SyncDirectory
        for local_dir in self.sync_directories:
            if local_dir.id_ not in remote_dir_dict.keys():
                # 対応するリモートなし→新規作成
                try:
                    remote_dir = SyncDirectory.create(remote_root.path_ / local_dir.path_.stem, local_dir.id_)
                    remote_root.sync_directories.append(remote_dir)
                except FileExistsError as e:
                    buffer = io.StringIO()
                    with redirect_stdout(buffer):
                        toast(
                            'Conflict on remote', 
                            'A folder with the same name already exists in the remote.', 
                        )
                    captured_output = buffer.getvalue()
                    return
                remote_dir_dict[remote_dir.id_] = remote_dir
        print('\n'.join([f'{local_dir.path_.stem} - {remote_dir_dict[id_].path_.stem}' for id_, local_dir in local_dir_dict.items()]))
        # 同期開始
        for local_dir in self.sync_directories.copy():
            remote_dir = remote_dir_dict[local_dir.id_]
            local_dir.locked = False
            remote_dir = local_dir.sync(remote_dir)
            # 削除チェック
            if not local_dir.path_.exists():
                self.sync_directories = [dir_ for dir_ in self.sync_directories if dir_ != local_dir]
                remote_root.sync_directories = [remote_dir if dir_.id_ == remote_dir.id_ else dir_ for dir_ in remote_root.sync_directories]
            # 同期済みフォルダをリモート一覧から削除
            del remote_dir_dict[local_dir.id_]
        # ローカルから同期のなかったリモートをロック
        for remote_dir in remote_dir_dict.values():
            remote_dir.locked = True
        self.dump()
        remote_root.dump()


class RemoteRootDirectory(RootDirectory):
    """
    リモートフォルダ
    """

    def dump(self):
        return super().dump(settings.remote_dump_filename)


# シリアライズ処理
def sync_directory_representer(dumper: yaml.Dumper, data: SyncDirectory):
    return dumper.represent_mapping("!SyncDirectory", data.model_dump())

def sync_directory_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return SyncDirectory(**loader.construct_mapping(node, deep=True))

def local_directory_representer(dumper: yaml.Dumper, data: LocalRootDirectory):
    return dumper.represent_mapping("!LocalRootDirectory", data.model_dump())

def local_directory_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return LocalRootDirectory(**loader.construct_mapping(node, deep=True))

def remote_directory_representer(dumper: yaml.Dumper, data: RemoteRootDirectory):
    return dumper.represent_mapping("!RemoteRootDirectory", data.model_dump())

def remote_directory_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return RemoteRootDirectory(**loader.construct_mapping(node, deep=True))

yaml.add_representer(SyncDirectory, sync_directory_representer)
yaml.add_constructor("!SyncDirectory", sync_directory_constructor)

yaml.add_representer(LocalRootDirectory, local_directory_representer)
yaml.add_constructor("!LocalRootDirectory", local_directory_constructor)

yaml.add_representer(RemoteRootDirectory, remote_directory_representer)
yaml.add_constructor("!RemoteRootDirectory", remote_directory_constructor)