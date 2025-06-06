from pathlib import Path
from core.dirsync import LocalRootDirectory, RemoteRootDirectory
from config import settings
from config.settings import general_settings
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


scheduler: BackgroundScheduler = BackgroundScheduler()

def watch():
    if not settings.has_root_dirs():
        return
    local = LocalRootDirectory(path_=general_settings.local_directory)
    remote = RemoteRootDirectory(path_=general_settings.remote_directory)
    print('Local:')
    local.check()
    print('\nRemote:')
    remote.check()
    print('\nSync:')
    local.sync(remote)
    print('Completed')


def create_scheduler() -> BackgroundScheduler:
    scheduler.add_job(func=watch, trigger="interval", seconds=general_settings.sync_freq_minutes*60, next_run_time=datetime.now(), id="watch_sync")
    return scheduler


def start_scheduler():
    scheduler.start()