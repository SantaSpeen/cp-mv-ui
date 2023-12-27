#!/usr/local/bin/python3

import os
import shutil
import sys
import threading
import time

argv = sys.argv

cmd = "mv" if "mv" in argv[0] else "cp"

if not len(argv) == 3:
    print(f"Usage: {cmd} SOURCE DESTINATION")
    exit(127)


def _size(s):
    KB = 1024
    MB = KB * 1024
    GB = MB * 1024
    if s >= GB:
        return f"{s / GB:.2f}gb"
    elif s >= MB:
        return f"{s / MB:.2f}mb"
    elif s >= KB:
        return f"{s / KB:.2f}kb"
    else:
        return f"{s}b"


def _time():
    pass


def count_objects(folder_path):
    count = [0, 0, 0, 0]
    #        |  |  |  |
    #        |  |  |  total size
    #        |  |  files
    #        |  dirs
    #        total
    mdata = [[], []]
    #        |   |
    #        |   files path
    #        dirs path
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            file_path = os.path.join(root, f)
            try:
                count[3] += os.path.getsize(file_path)  # adding file size to count[3]
                mdata[1].append(file_path)
            except FileNotFoundError:
                print(f"Strange file: {file_path}")
        count[0] += len(dirs)
        count[1] += len(dirs)
        mdata[0] += [os.path.join(root, d) for d in dirs]
        count[0] += len(files)
        count[2] += len(files)

    return count, mdata


class ProgressBar:
    def __init__(self, count):
        self.work = True
        self.files = count[0]
        self.size = count[3]
        self.lock = threading.Lock()
        self.width, _ = shutil.get_terminal_size()

        self.file_counter = 0
        self.file_now_path = None
        self.file_now_size = 0

        self.size_counter = 0

    def update(self, s):
        # s - size delta (0.1s)
        self.size_counter += s
        with self.lock:
            rt = (self.size - s) / self.size
            rt_str = f"{rt:.2f} s" if rt != float('inf') else "..."
            info = f" {self.file_counter}/{self.files} {_size(s)}/s" # ETA: {rt_str}"

            progress = int((self.size_counter / self.size) * (self.width - len(info)))
            bar = f"[{'#' * progress}{' ' * ((self.width - len(info)) - progress)}]"
            print(f"\r{bar}{info}", end="", flush=True)
    
    def set_file(self, path, size):
        self.file_counter += 1
        self.file_now_path = path
        self.file_now_size = size

    def worker(self):
        while self.work:
            if self.file_counter == 0:
                time.sleep
                continue
            self.width, _ = shutil.get_terminal_size()
            time.sleep(0.1)


def main():
    src = argv[1]
    dst = argv[2]

    if not os.path.exists(src):
        print(f"Invalid arguments")
        exit(127)

    print("Counting objects in folder..", end="", flush=True)
    count, mdata = count_objects(src)
    pb = ProgressBar(count)
    print(f"\r{count}", end="", flush=True)
    print(f"\rCopying files: {count[0]}; Size: {_size(count[3])}", flush=True)

    if not os.path.exists(dst) and not os.path.isfile(src):
        os.makedirs(dst)


if __name__ == "__main__":
    main()
    print()
