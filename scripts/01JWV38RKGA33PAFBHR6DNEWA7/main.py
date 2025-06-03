from pathlib import Path
from core.dirsync import SyncDirectory


def main(local_sync: SyncDirectory, remote_sync: SyncDirectory, modified_files: list[Path], removed_files: list[Path]):
    """
    Resize image.

    Args:
        local_sync (SyncDirectory): The local directory involved in synchronization.
        remote_sync (SyncDirectory): The remote directory involved in synchronization.
        modified_files (list[Path]): A list of file paths that have been modified.
        removed_files (list[Path]): A list of file paths that have been removed.
    """
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