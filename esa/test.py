from esa import sa, Workers, Manager
import time

# simauto = sa("C:/PowerWorld20/PWcases/PWcases/UIUC150Original/UIUC150_JAN-15-2016_Etime_Johnsonville_CT.PWB")
# print(simauto.getParametersSingleElement(element_type='BUS', field_list=['BusName', 'BusNum'], value_list=[0, 1]))


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


worker = Workers(number=2, file_path="C:/Users/maomz/Case/UIUC150_JAN-15-2016_Etime_Johnsonville_CT.PWB")
worker.start()

boss = Manager()
boss.addTask(tasks)
boss.start()

# boss.onSingleResult(some_function)


while True:
    print(boss.management)
    time.sleep(2)