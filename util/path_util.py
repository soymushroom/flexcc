from pathlib import Path


def is_subpath(parent: Path, child: Path) -> bool:
    try:
        # 絶対パスに変換して比較
        child = child.resolve(strict=False)
        parent = parent.resolve(strict=False)
        # path_a が path_b の下にあるか確認
        child.relative_to(parent)
        return True
    except ValueError:
        return False