import subprocess, sys

args = sys.argv

num = int(args[1])
target = [sys.executable, 'Worker.py', args[2], args[3], args[4]]


plist = []
print("Wake up %s workers ..." % num)
for i in range(num):
    plist.append(subprocess.Popen(target))
    # time.sleep(0.05)

#
exit_codes = [p.wait() for p in plist]