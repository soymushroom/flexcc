from pathlib import Path
from core.dirsync import SyncDirectory


def main(# --- DO NOT DELETE | 削除厳禁: System Reserved ---
    source_dir: SyncDirectory, dest_dir: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    # --- END ---
):
    '''同期対象フォルダ、ファイルの情報を出力するだけのスクリプトです。

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
    '''
    
    print(f"Source Path: {str(source_dir.path_)}")

    print(f"Destination Path: {str(dest_dir.path_)}")

    print("Modified Files: ")
    if modified_files:
        for p in modified_files:
            print(f"  {str(p)}")
    else:
        print("  * None *")
    
    print("Removed Files: ")
    if removed_files:
        for p in removed_files:
            print(f"  {str(p)}")
    else:
        print("  * None *")
