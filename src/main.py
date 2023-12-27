#!/usr/local/bin/python3

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


def worker(pb, c, m):
    start_time = time.time()
    for i in range(pb.max_value + 1):
        time.sleep(0.1)
        elapsed_time = time.time() - start_time
        speed = i / elapsed_time if elapsed_time > 0 else 0
        pb.update(i, speed)


def main():
    src = argv[1]
    dst = argv[2]

    if not os.path.exists(src):
        print(f"Invalid arguments")
        exit(127)

    if not os.path.exists(dst) and not os.path.isfile(src):
        os.makedirs(dst)

    print("Counting objects in folder..", end="", flush=True)
    c, m = count_objects(src)
    print(f"\r{c}", end="", flush=True)
    print(f"\rCopying files: {c[0]}, {c[3] / (1024.0 * 1024.0):.1f}mb", flush=True)

    pb = ProgressBar(c[0])
    pt = threading.Thread(target=worker, args=(pb, c, m))
    pt.start()
    pt.join()


if __name__ == "__main__":
    main()
    print()
