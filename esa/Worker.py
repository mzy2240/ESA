import paho.mqtt.client as mqtt
from .SimautoWrapper import PYSimAuto
import time, random, string, json, psutil
from ast import literal_eval
import sys


def init_mqtt(client):
    client.on_connect = on_connect
    client.on_message = on_message
    # client.on_publish = on_publish
    return client


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connect to the broker successfully!\n%s is online!" % worker_id)


def on_publish(client, userdata, mid):
    print("publish =>", userdata)


def on_message(client, userdata, msg):
    # print(msg.topic+" "+str(msg.payload))
    if 'task' in msg.topic:
        # print("Here")
        tasks = literal_eval(msg.payload.decode())
        task_id = tasks[0]
        for index, task in enumerate(tasks[1:]):
            print(task)
            func = task[0]
            args = task[1:]
            try:
                method_to_call = getattr(sim_server, func)
                payload = method_to_call(*args)
                if payload:
                    final_ts = payload[2][-1]
                    # client.publish("progress", str(('done', worker_id, task_id, index)))
            except Exception:
                raise ('bad execution: %s' % str(Exception))
        # time.sleep(2)     # do the task
        client.publish("feedback", str(('done', worker_id, task_id, final_ts[0])))
    elif 'broadcast' in msg.topic:
        if 'disconnect' in msg.payload.decode() and worker_id in msg.payload.decode():
            if normal_mode:
                print('Job done! %s will leave now.' % worker_id)
                client.disconnect()
        elif 'fallin' in msg.payload.decode():
            worker.publish("registration", json.dumps({'id': worker_id, 'hardware': worker_hardware}))


args = sys.argv
if len(args) == 1:
    # ip = "127.0.0.1"
    ip = "165.91.215.167"
    port = 1883
elif len(args) == 2:
    ip = args[1]
    port = 1883
else:
    ip = args[1]
    port = int(args[2])
    file_path = args[3]

normal_mode = True
worker_hardware = [psutil.cpu_count(False), psutil.cpu_freq().max, psutil.virtual_memory().free]
# file_path = "C:/PowerWorld20/PWcases/PWcases/UIUC150Original/UIUC150_JAN-15-2016_Etime_Johnsonville_CT.PWB"
# file_path = "C:/Users/maomz/Case/UIUC150_JAN-15-2016_Etime_Johnsonville_CT.PWB"
sim_server = PYSimAuto(file_path)
worker_id = "Worker_%s" % ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
worker = init_mqtt(mqtt.Client(worker_id))
#worker.connect("127.0.0.1")

worker.connect(ip, port)
worker.publish("registration", json.dumps({'id': worker_id, 'hardware': worker_hardware}))
worker.subscribe("broadcast")
worker.subscribe("task/%s" % worker_id)
# client.loop_start()

# while True:
#     time.sleep(0.5)
#     client.publish("task", "TESTTEST")

worker.loop_forever()