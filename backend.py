from pathlib import Path
import yaml
from core.copy import LocalRootDirectory, RemoteRootDirectory
from config import settings
from config.settings import preferences
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime


local: LocalRootDirectory
remote: RemoteRootDirectory
def init():
    global local
    global remote
    local = LocalRootDirectory(path_=preferences.LocalDirectory)
    remote = RemoteRootDirectory(path_=preferences.RemoteDirectory)


def watch():
    print('Local:')
    local.check()
    print('\nRemote:')
    remote.check()
    print('\nSync:')
    local.sync(remote)
    print('Completed')


def get_scheduler() -> BackgroundScheduler:
    scheduler: BackgroundScheduler = BackgroundScheduler()
    scheduler.add_job(func=watch, trigger="interval", seconds=60, next_run_time=datetime.now())
    return scheduler


init()