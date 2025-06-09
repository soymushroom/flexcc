from pathlib import Path
from core.dirsync import SyncDirectory
from tqdm import tqdm
import shutil


def main(# --- DO NOT DELETE | 削除厳禁: System Reserved ---
    source_dir: SyncDirectory, dest_dir: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    # --- END ---
    archive_to: Path, 
    extensions: str="*"
):
    '''同期によって削除対象になったリモートファイルを指定したフォルダへ退避します。

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
    archive_to : Path
        削除対象のファイルを退避させるフォルダを指定する。
    extensions : str, optional
        対象とする画像ファイルの拡張子をセミコロン区切りで指定する。規定値は "*"。
        大文字小文字は区別しない。"*" ですべての拡張子を対象とする。
        例: jpg;jpeg;png;
    '''
    
    # 拡張子判定
    if "*" in extensions:
        archived_paths = removed_files
    else:
        extensions = extensions.lower().replace(" ", "").split(";")
        archived_paths = [f for f in removed_files if f.suffix[1:].lower() in extensions]

    # ローカルフォルダのリネームに同期
    is_source_renamed = dest_dir.path_.stem != source_dir.path_.stem
    old_export_dir = archive_to / dest_dir.path_.stem
    if is_source_renamed and old_export_dir.exists():
        new_export_dir = archive_to / source_dir.path_.stem
        print(f'Rename export folder: \n{old_export_dir} \n > {new_export_dir}')
        old_export_dir.rename(new_export_dir)

    # 出力先フォルダを作成（存在しない場合）
    archive_to.mkdir(parents=True, exist_ok=True)

    # アーカイブ
    if len(archived_paths) > 0:
        print("Archive files: ")
        with tqdm(archived_paths) as pbar:
            for archived_path in pbar:
                pbar.set_description(f"{archived_path.name}")

                # コピー
                copy_from = dest_dir.path_ / archived_path
                copy_to = archive_to / source_dir.path_.stem / archived_path
                copy_to.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(copy_from, copy_to)