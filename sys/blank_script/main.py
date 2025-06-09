from pathlib import Path
from core.dirsync import SyncDirectory


def main(# --- DO NOT DELETE | 削除厳禁: System Reserved ---
    source_dir: SyncDirectory, dest_dir: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    # --- END ---

):
    """_summary_

    Parameters
    ----------
    <hide>
    # System-reserved
    source_dir : SyncDirectory
        同期を実行する際に同期元となるフォルダ。
    dest_dir : SyncDirectory
        同期を実行する際に同期先となるフォルダ。
    modified_files : list[Path]
        同期を実行する際に変更または追加されるファイルのリスト。
    removed_files : list[Path]
        同期を実行する際に削除されるファイルのリスト。
    # End System-reserved
    </hide>
    
    """
    
    print('Hello World!')