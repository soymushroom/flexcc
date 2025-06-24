from core.dirsync import LocalRootDirectory, RemoteRootDirectory
from pydantic import BaseModel
from pathlib import Path
from typing import ClassVar, Any
import shutil


class ScriptDebugger(BaseModel):
    
    ORIGIN_DIR: ClassVar[Path] = (Path('debug') / 'origin').resolve()
    RESULT_DIR: ClassVar[Path] = (Path('debug') / 'result').resolve()
    BACKUP_DIR: ClassVar[Path] = RESULT_DIR / 'bak'

    script_id: str
    root_local: LocalRootDirectory = LocalRootDirectory(path_=RESULT_DIR / 'src')
    root_remote: RemoteRootDirectory = RemoteRootDirectory(path_=RESULT_DIR / 'dst')


    def run(self, **kwargs):
        dirs = [
            ScriptDebugger.ORIGIN_DIR, 
            ScriptDebugger.RESULT_DIR, 
            ScriptDebugger.BACKUP_DIR
        ]
        for dir_ in dirs:
            dir_.mkdir(parents=True, exist_ok=True)
        if ScriptDebugger.RESULT_DIR.exists():
            shutil.rmtree(ScriptDebugger.RESULT_DIR)
        shutil.copytree(ScriptDebugger.ORIGIN_DIR, ScriptDebugger.RESULT_DIR)
        print('Local:')
        self.root_local.check()
        print('\nRemote:')
        self.root_remote.check()
        print('\nSync:')
        self.root_local.sync(self.root_remote, 'debug', self.script_id, kwargs)
        print('Completed')
        return self