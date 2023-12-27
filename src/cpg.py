#!/bin/python3

import os
import sys
import shutil
import threading
import time

argv = sys.argv

cmd = "mv" if "mv" in argv[0] else "cp"

if not len(argv) == 3:
    print(f"Usage: {cmd} SOURCE DESTINATION")
    exit(127)


def count_objects(folder_path):
    count = [0, 0, 0, 0]
    #        |  |  |  |
    #        |  |  |  total size
    #        |  |  files
    #        |  dirs
    #        total
    mdata = [[], []]
    for root, dirs, files in os.walk(folder_path):
        count[0] += len(dirs)
        count[1] += len(dirs)
        mdata[0] += [os.path.join(root, d) for d in dirs]
        count[0] += len(files)
        count[2] += len(files)
        for f in files:
            file_path = os.path.join(root, f)
            count[3] += os.path.getsize(file_path)  # adding file size to count[3]
            mdata[1].append(file_path)

    return count, mdata


class ProgressBar:
    def __init__(self, max_value):
        self.max_value = max_value
        self.lock = threading.Lock()
        w, _ = shutil.get_terminal_size()
        self.width = w - len(str(self.max_value)) * 2 - 32

    def update(self, now, speed):
        with self.lock:
            progress = int((now / self.max_value) * self.width)
            remaining_time = (self.max_value - now) / speed if speed > 0 else float('inf')
            remaining_time_str = f"{remaining_time:.2f} s" if remaining_time != float('inf') else "..."
            speed_str = f"{speed:.2f} Mb/s"
            bar = f"[{'#' * progress}{' ' * (self.width - progress)}] {now}/{self.max_value} {speed_str} ETA: {remaining_time_str}"
            print(f"\r{bar}", end="", flush=True)


def worker(pb, max_value):
    start_time = time.time()
    for i in range(max_value + 1):
        time.sleep(0.1)  # Имитация работы
        elapsed_time = time.time() - start_time
        speed = i / elapsed_time if elapsed_time > 0 else 0
        pb.update(i, speed)


def main():
    if not os.path.exists(f"./{argv[1]}") or not os.path.exists(f"./{argv[2]}"):
        print(f"Invalid arguments")
        exit(127)

    src = argv[1]
    dst = argv[2]

    print("Counting objects in folder..", end="", flush=True)
    c, mdata = count_objects(src)
    print(f"\r{c}", end="", flush=True)
    print(f"\rCopying files: {c[0]}, {c[3] / (1024.0 * 1024.0):.1f}mb", flush=True)

    max_value = c[0]
    pb = ProgressBar(max_value)
    progress_thread = threading.Thread(target=worker, args=(pb, max_value))
    progress_thread.start()
    progress_thread.join()


if __name__ == "__main__":
    main()
    print()
