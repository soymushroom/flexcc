from pydantic import BaseModel, field_validator
import yaml
from pathlib import Path
from os import makedirs

# 定数
sync_dir_ext = '._fxcc_sync'
root_dir_ext = '._fxcc_root'
cache_dir: Path = Path("cache")
if not cache_dir.exists():
    makedirs(cache_dir, exist_ok=True)
local_dump_filename: Path = cache_dir / f"local{root_dir_ext}"
remote_dump_filename: Path = cache_dir / f"remote{root_dir_ext}"
console_refresh_interval_sec: int = 15

# ユーザー設定
class Preferences(BaseModel):
    """
    ユーザー設定を保持するクラス
    """

    LocalDirectory: Path
    RemoteDirectory: Path
    SyncFreqMinutes: int
    HoldAfterCreatedDays: int
    HoldAfterModifiedDays: int
    ServerPort: int

def preferences_representer(dumper: yaml.Dumper, data: Preferences):
    return dumper.represent_mapping("!Preferences", data.model_dump())

def preferences_constructor(loader: yaml.Loader, node: yaml.MappingNode):
    return Preferences(**loader.construct_mapping(node, deep=True))

yaml.add_representer(Preferences, preferences_representer)
yaml.add_constructor("!Preferences", preferences_constructor)


preferences: Preferences
preferences = yaml.load((Path('config') / 'preferences.yaml').read_text(encoding='utf8'), Loader=yaml.Loader)