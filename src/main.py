#!/usr/local/bin/python3
import glob
import os
import shutil
import sys
import threading
import time

argv = sys.argv

cmd = "mv" if "mv" in argv[0] else "cp"

if len(argv) < 2:
    print(f"Usage: {cmd} <source> <destination>")
    exit(1)


def _size(size):
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size >= 1024 and i < 4:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def _time(seconds):
    units = [('d', 24 * 60 * 60), ('h', 60 * 60), ('m', 60), ('s', 1)]
    components = []

    for unit, divisor in units:
        value = seconds // divisor
        if value > 0:
            components.append(f"{int(value)}{unit}")
            seconds %= divisor

    return ' '.join(components) if components else "0s"


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
                count[3] += os.path.getsize(file_path)
                mdata[1].append(file_path)
            except FileNotFoundError:
                print(f"{file_path}: File listed, but not found.")
            except PermissionError:
                print(f"{file_path}: Permission denied.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
        count[0] += len(dirs)
        count[1] += len(dirs)
        mdata[0] += [os.path.join(root, d) for d in dirs]
        count[0] += len(files)
        count[2] += len(files)

    if os.path.isfile(folder_path):
        try:
            count[3] += os.path.getsize(folder_path)
            mdata[1].append(folder_path)
        except FileNotFoundError:
            print(f"{folder_path}: File listed, but not found.")
        except PermissionError:
            print(f"{folder_path}: Permission denied.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        count[0] = 1
        count[2] = 1

    return count, mdata


class ProgressBar:
    def __init__(self, count):
        self.work = True
        self.aborted = False
        self.count = count
        self.files = count[2]
        self.size = count[3]
        self.lock = threading.Lock()
        self.width, _ = shutil.get_terminal_size()

        self.file_counter = 0
        self.file_now_path = None

        self.size_counter = 0

    def update(self, s, rt, last=0.0):
        # s - size delta (0.1s)
        # rt - remaining time
        # last - working time on last msg
        with self.lock:
            c = f" {self.file_counter}/{self.files}" if not last else \
                f"{self.files} file{'s' if self.files > 1 else ''}, " \
                + f"{self.count[1]} dir{'s' if self.count[1] > 1 else ''}," if self.count[1] > 0 else ''
            sz = f"{_size(s * 50)}/s" if not last else f"{_size(self.size)}, {_size(self.size / last)}/s, "
            rt_str = _time(rt) if rt != float('inf') else "..."
            eta = f"ETA: {rt_str}" if not last else _time(last)
            info = f" {c} {sz} {eta}"

            progress = int((self.size_counter / self.size) * (self.width - len(info) - 2))
            bar = f"[{'#' * progress}{' ' * ((self.width - len(info)) - progress - 2)}]"
            print(f"\r{bar}{info}", end="", flush=True)

    def set_file(self, path):
        self.file_counter += 1
        self.file_now_path = path

    def worker(self):
        self.update(0, 0)
        last_size = 0
        last_file = 0
        size_deltas = []
        rts = []
        time_start = time.monotonic()
        while self.work:
            try:
                if self.file_counter != last_file:
                    last_size = 0
                    last_file = self.file_counter

                self.width, _ = shutil.get_terminal_size()

                # Get the size of the current file
                if self.file_now_path is not None and os.path.exists(self.file_now_path):
                    now_size = os.path.getsize(self.file_now_path)
                    # Calculate the size delta
                    size_delta = now_size - last_size
                    self.size_counter += size_delta
                    last_size = now_size
                    # Calculate the remaining time
                    remaining_files = self.files - self.file_counter
                    rt = (remaining_files * size_delta) / self.size
                    # Collect size_delta and rt values
                    size_deltas.append(size_delta)
                    rts.append(rt)
                    if len(size_deltas) == 15:
                        avg_size_delta = sum(size_deltas) / 15
                        avg_rt = sum(rts) / 15
                        self.update(avg_size_delta, avg_rt)
                        size_deltas = []
                        rts = []

            except FileNotFoundError:
                continue
            except PermissionError:
                print(f"{self.file_now_path}: Permission denied.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
            time.sleep(0.01)

        self.size_counter = self.size
        self.file_counter = self.files
        if not self.aborted:
            time_end = time.monotonic()
            self.update(0, 0, time_end - time_start)


class Copy:

    def __init__(self, pb: ProgressBar, mdata, src, dst):
        self.pb = pb
        self.dirs = mdata[0]
        self.files = mdata[1]
        self.src = src
        self.dst = dst

    def _get_new_path(self, path):
        common_path = os.path.commonpath([self.src, path])
        relative_path = os.path.relpath(path, common_path)
        # if os.path.isfile(path) and relative_path == '.':
        #     return self.dst
        return os.path.join(self.dst, relative_path)

    def copy_files(self):
        for src_file in self.files:
            dst_file = self._get_new_path(src_file)
            try:
                dst_dir = os.path.dirname(dst_file)
                os.makedirs(dst_dir, exist_ok=True)
                self.pb.set_file(dst_file)
                # noinspection PyTypeChecker
                shutil.copy(src_file, dst_file)
                # print(src_file, dst_file)
            except FileNotFoundError:
                print(f"{src_file}: File not found.")
                # raise FileExistsError
            except PermissionError:
                print(f"{src_file}: Permission denied.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")


def main():
    src = argv[1:-1]
    dst = argv[-1:][0]

    if len(src) == 1:
        src = src[0]
        dirs = glob.glob(src)
        if len(dirs) == 0 and isinstance(src, str) and not os.path.exists(src):
            print(f"No matching found: {src}")
            exit(127)
        elif len(dirs) == 1:
            src = dirs[0]
            dirs = False
    else:
        dirs = src

    print("Counting objects in folder..", end="", flush=True)

    _cache = []
    if dirs:
        count, mdata = [0, 0, 0, 0], [[], []]
        for i in dirs:
            c, m = count_objects(i)
            _cache.append([c, m])
            for j, v in enumerate(c):
                count[j] += v
            for j, v in enumerate(m):
                mdata[j] += v
    else:
        count, mdata = count_objects(src)
    pb = ProgressBar(count)
    print(f"\r{count}", end="", flush=True)
    print(f"\r{'Copying' if cmd == 'cp' else 'Moving'} objects: {count[0]}; Size: {_size(count[3])}", flush=True)

    t = threading.Thread(target=pb.worker)

    def do(d, s, m):
        if not os.path.exists(d) and not os.path.isfile(s):
            os.makedirs(d)
        cp = Copy(pb, m, s, d)
        cp.copy_files()
        if cmd == 'mv':
            shutil.rmtree(s)

    try:
        t.start()
        if isinstance(src, list):
            for i, isrc in enumerate(src):
                _, m = _cache[i]
                _dst = os.path.join(dst, isrc)
                do(_dst, isrc, m)
        else:
            do(dst, src, mdata)
    except KeyboardInterrupt:
        print("\nAborted")
        pb.aborted = True
    finally:
        pb.work = False
    t.join()


if __name__ == "__main__":
    main()
    print()
