from pathlib import Path
from core.dirsync import SyncDirectory
from tqdm import tqdm
import shutil


def main(
    source_dir: SyncDirectory, dest_dir: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    archive_to: Path, 
    extensions: str="*"
):
    """
    同期によって削除対象になったリモートファイルを、指定したフォルダへ退避します。

    Args:
        <hide>
        source_dir (SyncDirectory): The source directory involved in synchronization.
        dest_dir (SyncDirectory): The destination directory involved in synchronization.
        modified_files (list[Path]): A list of file paths(relative) that have been modified.
        removed_files (list[Path]): A list of file paths(relative) that have been removed.
        </hide>
        destination (pathlib.Path):
            削除対象のファイルを退避させるフォルダを指定する。
        
        extensions (str): 
            対象とする画像ファイルの拡張子をセミコロン区切りで指定する。
            大文字小文字は区別しない。
            * ですべての拡張子を対象とする。
            例: jpg;jpeg;png;
    """
    print("Script 3")
    print(f"Local: {str(source_dir.path_)}")
    print(f"Remote: {str(dest_dir.path_)}")
    print("Modified: ")
    if modified_files:
        for p in modified_files:
            print(f"  {str(p)}")
    else:
        print("  None")
    print("Removed: ")
    if removed_files:
        for p in removed_files:
            print(f"  {str(p)}")
    else:
        print("  None")

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
        print("Resize files: ")
        with tqdm(archived_paths) as pbar:
            for archived_path in pbar:
                pbar.set_description(f"{archived_path.name}")

                # 保存先ファイルパスを構築
                output_path = archive_to / source_dir.path_.stem / archived_path
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # コピー
                source_path = source_dir.path_ / archived_path
                shutil.copy2(source_path, output_path)