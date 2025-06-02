from pathlib import Path


def main(synced_locals: list[Path], synced_remotes: list[Path]):
    """
    指定された名前を指定された回数の "Hello " とともに返す関数。
    """
    for p in synced_locals:
        print(str(p.absolute()))