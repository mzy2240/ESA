from Manager import Manager
from Workers import Workers
import time
from ProgressBar import progressbar

# Define a function that will be triggered by an event
def some_function(result):
    print("Triggered!")
    print(result)


# Create your tasks
ObjectType = 'TSContingencyElement'
FieldList = '[TSTimeInSeconds,WhoAmI,TSEventString,TSCTGName]'
tasks = []
for i in range(10):
    ValueList = '[%s,"Branch \'144\' \'101\' \'1\'","OPEN BOTH","My Transient Contingency"]' % 120
    tasks.append([120, ("createData", ObjectType, FieldList, ValueList), ("tsSolve", "My Transient Contingency"),
           ("tsGetContingencyResults", "My Transient Contingency", ['"Bus 4 | frequency"']),
           ("delete", ObjectType)])


worker = Workers(number=2, file_path="C:/Users/yijin/Desktop/Research/case/WSCC9-BusSystem-SimAuto/UIUC150_JAN-15-2016_Etime_Johnsonville_CT_v20.PWB"
)
worker.start()

boss = Manager()

boss.start()
boss.addTask(tasks)
# boss.onSingleResult(some_function)


#while True:
 #   print(boss.management)
#    time.sleep(2)

progressbar = progressbar()
progressbar.start()