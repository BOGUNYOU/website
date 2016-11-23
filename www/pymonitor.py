#!usr/bin/python
# _*_ coding:utf-8 _*_
import os, sys, time, subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def log(s):
    print '[monitor] %s' %s


class MyFileSystemEventHandle(FileSystemEventHandler):
    def __init__(self, fn):
        super(MyFileSystemEventHandle, self).__init__()
        self.restart = fn

    def on_any_event(self, event):
        if event.src_path.endswith('.py'):
            log('Python source file changed: %s' % event.src_path)
            self.restart()

commond = ['echo', 'ok']
process = None

def kill_process():
    global process
    if process:
        log('Kill process [%s]...' % process.pid)
        process.kill()
        process.wait()
        log('Process ended with code %s.' % process.returncode)
        process = None


def start_process():
    global process, commond
    log('start process %s' % ' '.join(commond))
    process = subprocess.Popen(commond, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restart_process():
    kill_process()
    start_process()

def start_watch(path, callback):
    observer = Observer()
    observer.schedule(MyFileSystemEventHandle(restart_process), path, recursive=True)
    observer.start()
    log('Watching directory %s ...' % path)
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__=='__main__':
    argv= sys.argv[1:]
    if not argv:
        print ('usage: ./pymonitor your-script.py')
        exit(0)
    if argv[0] != 'python':
        argv.insert(0,'python')
    commond = argv
    path = os.path.abspath('.')
    start_watch(path,None)