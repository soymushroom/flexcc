from pathlib import Path
from core.dirsync import SyncDirectory
from typing import Literal
from PIL import Image
from tqdm import tqdm


def main(
    source_dir: SyncDirectory, dest_dir: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    export_to: Path, 
    extensions: str="jpg; jpeg; png; gif; bmp; webp; tiff; tif; heic; heif; ", 
    mode: Literal["percentage", "long_side", "short_side", "width", "height"]="percentage",
    value: int=100,
    jpeg_quality: int=92, 
    allow_enlarge: bool=False
):
    """
    画像ファイルをリサイズして指定したフォルダにバックアップします。

    Args:
        <hide>
        source_dir (SyncDirectory): The source directory involved in synchronization.
        dest_dir (SyncDirectory): The destination directory involved in synchronization.
        modified_files (list[Path]): A list of file paths(relative) that have been modified.
        removed_files (list[Path]): A list of file paths(relative) that have been removed.
        </hide>
        export_to (pathlib.Path):
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
    extensions = extensions.lower().replace(" ", "").split(";")
    modified_img_paths = [f for f in modified_files if f.suffix[1:].lower() in extensions]
    removed_img_paths = [f for f in removed_files if f.suffix[1:].lower() in extensions]
    
    # ファイル削除
    if len(removed_img_paths) > 0:
        print("Remove files: ")
        with tqdm(removed_img_paths) as pbar:
            for img_path in pbar:
                pbar.set_description(f"{img_path.name}")
                output_path = export_to / dest_dir.path_.stem / img_path
                output_path.unlink(missing_ok=True)

    # ローカルフォルダのリネームに同期
    is_source_renamed = dest_dir.path_.stem != source_dir.path_.stem
    old_export_dir = export_to / dest_dir.path_.stem
    if is_source_renamed and old_export_dir.exists():
        new_export_dir = export_to / source_dir.path_.stem
        print(f'Rename export folder: \n{old_export_dir} \n > {new_export_dir}')
        old_export_dir.rename(new_export_dir)

    # 出力先フォルダを作成（存在しない場合）
    export_to.mkdir(parents=True, exist_ok=True)

    # リサイズ実行
    if len(modified_img_paths) > 0:
        print("Resize files: ")
        with tqdm(modified_img_paths) as pbar:
            for img_path in pbar:
                pbar.set_description(f"{img_path.name}")
                with Image.open(source_dir.path_ / img_path) as img:
                    original_width, original_height = img.size

                    # 拡大禁止の場合のチェック
                    def get_resizability(new_w, new_h):
                        return allow_enlarge or new_w < original_width or new_h < original_height

                    # 新しいサイズを計算
                    if mode == "percentage":
                        scale = value / 100
                        new_width = int(original_width * scale)
                        new_height = int(original_height * scale)
                    elif mode == "long_side":
                        if original_width >= original_height:
                            scale = value / original_width
                        else:
                            scale = value / original_height
                        new_width = int(original_width * scale)
                        new_height = int(original_height * scale)
                    elif mode == "short_side":
                        if original_width <= original_height:
                            scale = value / original_width
                        else:
                            scale = value / original_height
                        new_width = int(original_width * scale)
                        new_height = int(original_height * scale)
                    elif mode == "width":
                        scale = value / original_width
                        new_width = value
                        new_height = int(original_height * scale)
                    elif mode == "height":
                        scale = value / original_height
                        new_height = value
                        new_width = int(original_width * scale)
                    else:
                        # 不明なモード
                        continue

                    # リサイズが必要な場合のみ
                    if get_resizability(new_width, new_height):
                        resized = img.resize((new_width, new_height), Image.LANCZOS)
                    else:
                        resized = img.copy()

                    # 保存先ファイルパスを構築
                    output_path = export_to / source_dir.path_.stem / img_path
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # 拡張子で保存形式判定
                    ext = output_path.suffix.lower()
                    kwargs = {}
                    if ext in [".jpg", ".jpeg"]:
                        exif_bytes = img.info.get('exif')  # バイナリ形式のEXIFデータ
                        if exif_bytes is not None:
                            kwargs["exif"] = exif_bytes
                        resized.save(output_path, "JPEG", quality=jpeg_quality, **kwargs)
                    else:
                        resized.save(output_path)