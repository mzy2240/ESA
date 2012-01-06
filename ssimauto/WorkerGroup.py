import subprocess, sys

args = sys.argv
if len(args) == 1:
    num = 3
    target = [sys.executable, 'Worker.py']
elif len(args) == 2:
    print(args)
    num = int(args[1])
    target = [sys.executable, 'Worker.py']
elif len(args) == 3:
    num = int(args[1])
    target = [sys.executable, 'Worker.py', args[2]]
else:
    num = int(args[1])
    target = [sys.executable, 'Worker.py', args[2], args[3]]


plist = []
print("Wake up %s workers ..." % num)
for i in range(num):
    plist.append(subprocess.Popen(target))
    # time.sleep(0.05)

#
exit_codes = [p.wait() for p in plist]