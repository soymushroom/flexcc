from pathlib import Path
from core.dirsync import LocalRootDirectory, RemoteRootDirectory
from config import settings
from config.settings import preferences
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


scheduler: BackgroundScheduler = BackgroundScheduler()

def watch():
    if not settings.has_root_dirs():
        return
    local = LocalRootDirectory(path_=preferences.LocalDirectory)
    remote = RemoteRootDirectory(path_=preferences.RemoteDirectory)
    print('Local:')
    local.check()
    print('\nRemote:')
    remote.check()
    print('\nSync:')
    local.sync(remote)
    print('Completed')


def create_scheduler() -> BackgroundScheduler:
    scheduler.add_job(func=watch, trigger="interval", seconds=preferences.SyncFreqMinutes*60, next_run_time=datetime.now(), id="watch_sync")
    return scheduler


def start_scheduler():
    scheduler.start()