#!/usr/local/bin/python3
import glob
import os
import shutil
import sys
import threading
import time

argv = sys.argv

cmd = "mv" if "mv" in argv[0] else "cp"

if not len(argv) == 3:
    print(f"Usage: {cmd} <source> <destination>")
    exit(127)


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
        self.files = count[0]
        self.size = count[3]
        self.lock = threading.Lock()
        self.width, _ = shutil.get_terminal_size()

        self.file_counter = 0
        self.file_now_path = None

        self.size_counter = 0

    def update(self, s, rt):
        # s - size delta (0.1s), rt - remaining time
        self.size_counter += s
        with self.lock:
            rt_str = _time(rt) if rt != float('inf') else "..."
            info = f" {self.file_counter}/{self.files} {_size(s*10)}/s ETA: {rt_str}"

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
                    last_size = now_size
                    # Calculate the remaining time
                    remaining_files = self.files - self.file_counter
                    rt = (remaining_files * size_delta) / self.size
                    self.update(size_delta, rt)
            except FileNotFoundError:
                continue
            except PermissionError:
                print(f"{self.file_now_path}: Permission denied.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
            time.sleep(0.1)

        self.size_counter = self.size
        self.file_counter = self.files
        if not self.aborted:
            self.update(0, 0)


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
        return os.path.join(self.dst, relative_path)

    def create_dirs(self):
        for src_dir in self.dirs:
            dst_dir = self._get_new_path(src_dir)
            os.makedirs(dst_dir, exist_ok=True)
            self.pb.set_file(dst_dir)

    def copy_files(self):
        for src_file in self.files:
            dst_file = self._get_new_path(src_file)
            try:
                self.pb.set_file(dst_file)
                # noinspection PyTypeChecker
                shutil.copy(src_file, dst_file)
            except FileNotFoundError:
                print(f"{src_file}: File not found.")
            except PermissionError:
                print(f"{src_file}: Permission denied.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        self.pb.work = False


def main():
    src = argv[1]
    dst = argv[2]

    dirs = glob.glob(src)
    if len(dirs) == 0:
        print(f"No matching found: {src}")
        exit(127)
    elif len(dirs) == 1:
        src = dirs[0]
        dirs = False

    print("Counting objects in folder..", end="", flush=True)

    if dirs:
        count, mdata = [0, 0, 0, 0], [[], []]
        for i in dirs:
            c, m = count_objects(i)
            for j, v in enumerate(c):
                count[j] += v
            for j, v in enumerate(m):
                mdata[j] += v
    else:
        count, mdata = count_objects(src)
    pb = ProgressBar(count)
    cp = Copy(pb, mdata, src, dst)
    print(f"\r{count}", end="", flush=True)
    print(f"\r{'Copying' if cmd == 'cp' else 'Moving'} objects: {count[0]}; Size: {_size(count[3])}", flush=True)

    if not os.path.exists(dst) and not os.path.isfile(src):
        os.makedirs(dst)

    t = threading.Thread(target=pb.worker)
    try:
        t.start()
        cp.create_dirs()
        cp.copy_files()
        if cmd == 'mv':
            shutil.rmtree(src)
    except KeyboardInterrupt:
        print("\nAborted")
        pb.aborted = True
    finally:
        pb.work = False
    t.join()


if __name__ == "__main__":
    main()
    print()
