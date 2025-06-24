from pathlib import Path
import sys
if __name__ == '__main__':
    sys.path.append(str(Path(__file__).resolve().parents[2]))
from core.dirsync import SyncDirectory


def main(# --- DO NOT DELETE | 削除厳禁: System Reserved ---
    source_dir: SyncDirectory, dest_dir: SyncDirectory, modified_files: list[Path], removed_files: list[Path], 
    # --- END ---
    text: str='Hello World!'
):
    """指定した文字列を出力するだけのスクリプトです。

    Parameters
    ----------
    <hide>
    # System-reserved
    source_dir : SyncDirectory
        同期を実行する際に同期元となるディレクトリ。
    dest_dir : SyncDirectory
        同期を実行する際に同期先となるディレクトリ。
    modified_files : list[Path]
        同期を実行する際に変更または追加されるファイルのリスト。
    removed_files : list[Path]
        同期を実行する際に削除されるファイルのリスト。
    # End System-reserved
    </hide>
    text : str, optional
        表示する文字列を指定する。規定値は 'Hello World!'。
    """
    
    print(text)


if __name__ == '__main__':
    from debug.debugger import ScriptDebugger
    
    print(f'--- Start debug ---')
    id_ = Path(__file__).resolve().parent.name
    print(f'ID: {id_}')
    debugger = ScriptDebugger(script_id=id_)
    print(f'--- Sync debug directory ---')
    kwargs=dict(
        text="Hello debugger!"
    )
    debugger.run(**kwargs)