from pydantic import BaseModel, field_validator
import yaml
from pathlib import Path
import os
import ctypes
import shutil


# 定数
sync_dir_ext = '._fxcc_sync'
root_dir_ext = '._fxcc_root'
cache_dir: Path = Path("cache")
if cache_dir.exists():
    shutil.rmtree(cache_dir)
os.makedirs(cache_dir, exist_ok=True)
local_dump_filename: Path = cache_dir / f"local{root_dir_ext}"
remote_dump_filename: Path = cache_dir / f"remote{root_dir_ext}"
console_refresh_interval_sec: int = 15
preferences_path: Path = Path('config') / 'preferences.yaml'

# ユーザー設定
class Preferences(BaseModel):
    """
    ユーザー設定を保持するクラス
    """

    LocalDirectory: Path | None = None
    RemoteDirectory: Path | None = None
    SyncFreqMinutes: int = 5
    HoldAfterCreatedDays: int = 32
    HoldAfterModifiedDays: int = 8
    ServerPort: int = 28541


    def dump(self) -> str:
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(preferences_path))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(preferences_path), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        preferences_path.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')

def preferences_representer(dumper: yaml.Dumper, data: Preferences):
    return dumper.represent_mapping("!Preferences", data.model_dump())

def preferences_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return Preferences(**loader.construct_mapping(node, deep=True))

yaml.add_representer(Preferences, preferences_representer)
yaml.add_constructor("!Preferences", preferences_constructor)

# User Preferences
preferences: Preferences
if preferences_path.exists():
    preferences = yaml.load(preferences_path.read_text(encoding='utf8'), Loader=yaml.Loader)
else:
    preferences = Preferences()
    preferences.dump()

def has_root_dirs():
    return (
        preferences.LocalDirectory
        and preferences.RemoteDirectory
        and preferences.LocalDirectory.exists()
        and preferences.RemoteDirectory.exists()
    )