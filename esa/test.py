from Manager import Manager
import time


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


boss = Manager()

boss.start()
boss.addTask(tasks)
# boss.onSingleResult(some_function)


while True:
    print(boss.management)
    time.sleep(2)