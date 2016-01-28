#!/usr/bin/env python
"""Runs a celery worker, and reloads on a file change. Run as ./run_celery [directory]. If
directory is not given, default to cwd."""
import os
import sys
import signal
import time

import multiprocessing
import subprocess
import threading

import inotify.adapters


CELERY_CMD = tuple("celery -A amcat.amcatcelery worker -l info -Q amcat".split())
CHANGE_EVENTS = ("IN_MODIFY", "IN_ATTRIB", "IN_DELETE")
WATCH_EXTENSIONS = (".py",)

def watch_tree(stop, path, event):
    """
    @type stop: multiprocessing.Event
    @type event: multiprocessing.Event
    """
    path = os.path.abspath(path)

    for e in inotify.adapters.InotifyTree(path).event_gen():
        if stop.is_set():
            break

        if e is not None:
            _, attrs, path, filename = e

            if filename is None:
                continue

            if any(filename.endswith(ename) for ename in WATCH_EXTENSIONS):
                continue

            if any(ename in attrs for ename in CHANGE_EVENTS):
                event.set()


class Watcher(threading.Thread):
    def __init__(self, path):
        super(Watcher, self).__init__()
        self.celery = subprocess.Popen(CELERY_CMD)
        self.stop_event_wtree = multiprocessing.Event()
        self.event_triggered_wtree = multiprocessing.Event()
        self.wtree = multiprocessing.Process(target=watch_tree, args=(self.stop_event_wtree, path, self.event_triggered_wtree))
        self.wtree.start()
        self.running = True

    def run(self):
        while self.running:
            if self.event_triggered_wtree.is_set():
                self.event_triggered_wtree.clear()
                self.restart_celery()
            time.sleep(1)

    def join(self, timeout=None):
        self.running = False
        self.stop_event_wtree.set()
        self.wtree.join()
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

