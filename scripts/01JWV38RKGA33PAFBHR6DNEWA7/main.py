from pathlib import Path
from core.dirsync import SyncDirectory
from typing import Literal


def main(
    source_dir: SyncDirectory, dest_dir: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    destination: Path, 
    extensions: str="jpg; jpeg; png; gif; bmp; webp; tiff; tif; heic; heif; ", 
    mode: Literal["percentage", "long_side", "short_side", "width", "height"]="percentage",
    value: int=100,
    jpeg_quality: int=92, 
    allow_enlarge: bool=False
):
    """
    Resize image.

    Args:
        <hide>
        source_dir (SyncDirectory): The source directory involved in synchronization.
        dest_dir (SyncDirectory): The destination directory involved in synchronization.
        modified_files (list[Path]): A list of file paths that have been modified.
        removed_files (list[Path]): A list of file paths that have been removed.
        </hide>
        destination (pathlib.Path):
            リサイズされた画像を保存するフォルダを指定する。
        
        extensions (str): 
            対象とする画像ファイルの拡張子をセミコロン区切りで指定する。
            大文字小文字は区別しない。
            例: jpg;jpeg;png;

        mode (Literal["percentage", "long_side", "short_side", "width", "height"]): 
            リサイズ方法を指定するモード。
            - "percentage": 画像全体を指定された割合でリサイズ。
            - "long_side": 長辺を value に合わせてリサイズ（短辺は比率を維持）。
            - "short_side": 短辺を value に合わせてリサイズ（長辺は比率を維持）。
            - "width": 幅を value に固定、高さは比率で調整。
            - "height": 高さを value に固定、幅は比率で調整。

        value (int): 
            指定された mode に応じたリサイズの基準値。
            例: mode="percentage" の場合は割合(%)、mode="width" の場合はピクセル単位の幅など。

        jpeg_quality (int): 
            Jpeg保存時の品質。

        allow_enlarge (bool): 
            True にすると、元のサイズより大きくリサイズすることを許可する。
            False の場合、元のサイズより拡大されることはない。
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