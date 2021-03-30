import os
import shutil
import stat


def del_rw(action, name, exc):
    try:
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)
    except FileNotFoundError:
        pass


def rmdir(path):
    path = str(path)
    if os.name == "nt":
        path = "\\\\?\\" + path

    shutil.rmtree(path, onerror=del_rw)

