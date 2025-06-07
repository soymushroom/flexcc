from pathlib import Path
from core.dirsync import SyncDirectory
from typing import Literal


def main(
    local_sync: SyncDirectory, remote_sync: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    destination: Path, 
    mode: Literal["percentage", "long_side", "short_side", "width", "height"]="percentage",
    value: int=100,
    jpeg_quality: int=92, 
    allow_enlarge: bool=False
):
    """
    Resize image.

    Args:
        <hide>
        local_sync (SyncDirectory): The local directory involved in synchronization.
        remote_sync (SyncDirectory): The remote directory involved in synchronization.
        modified_files (list[Path]): A list of file paths that have been modified.
        removed_files (list[Path]): A list of file paths that have been removed.
        </hide>
        destination (pathlib.Path):
            リサイズされた画像を保存するフォルダ。

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
    print(f"Local: {str(local_sync.path_)}")
    print(f"Remote: {str(remote_sync.path_)}")
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