import subprocess
import sys


class Workers:

    def __init__(self, number=1, ip="165.91.215.167", port=1883, auto_shutdown=False, timeout=0, file_path=""):
        self.number = number
        self.ip=ip
        self.port=port
        self.auto_shutdown = auto_shutdown
        self.timeout = timeout
        self.file_path = file_path
        self.exit_codes = []

    def start(self):
        plist = []
        print("Wake up %s workers ..." % self.number)
        target = [sys.executable, 'Worker.py', self.ip, str(self.port), self.file_path]
        for i in range(self.number):
            plist.append(subprocess.Popen(target))


# TODO:
# 1. Change the arguments for worker.py
# 2. Add another thread for getting updates from workers
# 3. Change worker.py to have proper outputs to STDOUT/STDERR
# 4. Add other methods or properties
