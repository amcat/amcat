#!/usr/bin/env python3
"""Runs a celery worker, and reloads on a file change. Run as ./run_celery [directory]. If
directory is not given, default to cwd."""
import os
import sys
import signal
import time

import multiprocessing
import subprocess
import threading

import pyinotify

os.environ['DJANGO_SETTINGS_MODULE'] = os.environ.get('DJANGO_SETTINGS_MODULE', 'settings')

if len(sys.argv) > 2:
    CELERY_BIN = sys.argv[2]
else:
    CELERY_BIN = "celery"

CELERY_CMD = tuple("{} -A amcat.amcatcelery worker -l info -Q amcat".format(CELERY_BIN).split())

CHANGE_EVENTS = pyinotify.IN_DELETE | \
                pyinotify.IN_CREATE | \
                pyinotify.IN_MODIFY | \
                pyinotify.IN_ATTRIB | \
                pyinotify.IN_CLOSE_WRITE

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, trigger, **kargs):
        super().__init__(**kargs)
        self.trigger = trigger

    def process_default(self, event):
        if event.path.startswith("."):
            return

        if event.name.startswith("."):
            return

        if not event.name.endswith(".py"):
            return

        self.trigger.set()

class Watcher(threading.Thread):
    def __init__(self, path):
        super(Watcher, self).__init__()
        self.celery = subprocess.Popen(CELERY_CMD)
        self.wm = pyinotify.WatchManager()
        self.event_triggered_wtree = multiprocessing.Event()
        self.notifier = pyinotify.ThreadedNotifier(self.wm, EventHandler(self.event_triggered_wtree))
        self.notifier.start()
        self.wm.add_watch(path, CHANGE_EVENTS, rec=True)
        self.running = True

    def run(self):
        while self.running:
            if self.event_triggered_wtree.is_set():
                self.event_triggered_wtree.clear()
                self.restart_celery()
            time.sleep(1)

    def join(self, timeout=None):
        self.running = False
        self.celery.terminate()
        self.notifier.stop()
        self.celery.wait()
        self.notifier.join()
        super(Watcher, self).join(timeout=timeout)

    def restart_celery(self):
        self.celery.terminate()
        self.celery.wait()
        self.celery = subprocess.Popen(CELERY_CMD)


if __name__ == '__main__':
    watcher = Watcher(sys.argv[1] if len(sys.argv) > 1 else ".")
    watcher.start()

    signal.signal(signal.SIGINT, lambda signal, frame: watcher.join())
    signal.pause()

