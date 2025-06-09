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
general_settings_path: Path = Path('config') / 'general_settings.yaml'


# ユーザー設定
class GeneralSettings(BaseModel):
    """
    ユーザー設定を保持するクラス
    """

    local_directory: Path | None = None
    remote_directory: Path | None = None
    sync_freq_minutes: int = 15
    hold_after_created_days: int = 15
    hold_after_modified_days: int = 8
    server_port: int = 28541

    def dump(self) -> str:
        # 隠しファイル属性を解除
        FILE_ATTRIBUTE_HIDDEN = 0x2
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(general_settings_path))
        if attrs & FILE_ATTRIBUTE_HIDDEN:
            ctypes.windll.kernel32.SetFileAttributesW(str(general_settings_path), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        # 書き込み
        general_settings_path.write_text(yaml.dump(self, allow_unicode=True), encoding='utf8')

def general_settings_representer(dumper: yaml.Dumper, data: GeneralSettings):
    return dumper.represent_mapping("!GeneralSettings", data.model_dump())

def general_settings_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return GeneralSettings(**loader.construct_mapping(node, deep=True))

yaml.add_representer(GeneralSettings, general_settings_representer)
yaml.add_constructor("!GeneralSettings", general_settings_constructor)

# General Settings
general_settings: GeneralSettings
if general_settings_path.exists():
    general_settings = yaml.load(general_settings_path.read_text(encoding='utf8'), Loader=yaml.Loader)
else:
    general_settings = GeneralSettings()
    general_settings.dump()

def has_root_dirs():
    return (
        general_settings.local_directory
        and general_settings.remote_directory
        and general_settings.local_directory.exists()
        and general_settings.remote_directory.exists()
    )