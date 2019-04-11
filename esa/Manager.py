import paho.mqtt.client as mqtt
from queue import Queue, Empty
import time
import random
import string
import json
from ast import literal_eval
from tqdm import tqdm
from threading import Thread


class Manager:

    def __init__(self, auto_shutdown=False, dynamic_load_balance=False, save_to_excel=False, progressbar=False, visualization=False):
        self.__queue = Queue()
        self.__active = False
        # self.__thread = Thread(target=self.__run)
        self.auto_shutdown = auto_shutdown
        self.dynamic_load_balance = dynamic_load_balance
        self.save_to_excel = save_to_excel
        self.progressbar = progressbar
        self.visualization = visualization
        self.__handlers = {}
        self.__running = False
        self.__status = None
        self.__time = None
        self.__management = {}
        self.__final_result = []
        self.__pbar = None
        self.__pbars = {}
        self.__first = True
        self.id = "Boss_%s" % ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.boss = mqtt.Client(self.id)
        self.__mqtt_init__(self.boss)

    def __mqtt_init__(self, client):
        # client.on_connect = self.__mqtt_connect
        client.on_message = self.__mqtt_message
        # client.on_publish = self.__mqtt_publish

    def __mqtt_connect(self, *args):
        if args[3] == 0:
            print("Connect to the broker successfully!\n%s is online!" % self.id)

    def __mqtt_message(self, client, userdata, msg):
        # print(msg.topic, str(msg.payload))
        if "registration" in msg.topic:
            worker_info = json.loads(msg.payload.decode())
            workerid = worker_info['id']
            # print(worker_info)
            self.__management[workerid] = {
                'status': 'online',
                'machine': worker_info['machine'],
                'hardware': worker_info['hardware'],
                'task': None,
                'CRT': None,
                'start': None,
                'working_hours': 0,
                'task_count': 0,
                'efficiency': None
            }
            if self.__running:
                task = self.__obtain_task(workerid)
                if task:
                    # print(str(msg.payload))
                    if not self.progressbar:
                        print(self.time, "%s is online" % workerid)
                    self.__management[workerid]['task'] = task
                    self.__management[workerid]['start'] = time.time()
                    self.boss.publish("task/%s" % workerid, task, qos=2)

        elif "feedback" in msg.topic:
            payload = literal_eval(msg.payload.decode())
            workerid = payload[1]
            task_id = payload[-2]
            self.__management[workerid]['working_hours'] += time.time() - self.__management[workerid]['start']
            self.__management[workerid]['task_count'] += 1
            self.__management[workerid]['efficiency'] = round(self.__management[workerid]['working_hours']/self.__management[workerid]['task_count'],2)
            final_tp = float(payload[-1])
            self.__final_result.append(final_tp)
            if self.progressbar:
                self.__pbar.update(1)
            if self.visualization:
                self.__power_dashboard()
            if self.__running:
                self.__process("onSingleResult", final_tp)
                task = self.__obtain_task(workerid)
                if task:
                    self.__management[workerid]['status'] = 'online'
                    self.__management[workerid]['task'] = task
                    self.__management[workerid]['start'] = time.time()
                    self.boss.publish("task/%s" % workerid, task, qos=2)

    def __mqtt_publish(self, *args):
        print(str(args[2] - 2), "=> publish")

    def __obtain_task(self, worker_name):
        try:
            # heartbeat_check()
            task = self.__queue.get(block=False)
            return str(task)
        except Empty:
            try:
                if self.__no_unexpected_events():
                    self.__management[worker_name]['task'] = None
                    if self.__all_done():
                        self.__status = "Finished"
                        if self.progressbar:
                            self.__pbar.close()
                        self.__process("onFinish", self.__final_result)
                        if self.auto_shutdown:
                            self.boss.disconnect()
                return None
            except KeyError:
                pass

    def __process(self, event, result):
        if event in self.__handlers:
            [handler(result) for handler in self.__handlers[event]]

    def __no_unexpected_events(self):
        for worker_name, child_dict in self.__management.items():
            status, _, task, _ = child_dict.values()
            if 'offline' in status and task:
                """
                put the task back to the front of the queue
                clear the task of this user
                """
                self.__queue.put(task)
                self.__management[worker_name]['task'] = None
                return False
        return True

    def __all_done(self):
        for child_dict in self.__management.values():
            if child_dict['task']:
                return False
        return True

    def __register(self, event, handler):
        try:
            handlerList = self.__handlers[event]
        except KeyError:
            handlerList = []
            self.__handlers[event] = handlerList
        if handler not in handlerList:
            handlerList.append(handler)

    def __power_dashboard(self):
        self.boss.publish("dashboard", str(self.management))

    def start(self):
        self.__running = True
        self.__status = "Running"
        self.__time = time.time()
        # self.boss.connect("127.0.0.1")
        self.boss.connect("165.91.215.167")
        self.boss.subscribe("registration")
        self.boss.subscribe("feedback")
        self.boss.subscribe("heartbeat")
        self.boss.publish("broadcast", "fallin", qos=2)
        self.boss.loop_start()

    def pause(self):
        self.__running = False
        self.__status = "Paused"

    def resume(self):
        self.__running = True
        self.__status = "Running"
        self.boss.publish("broadcast", "fallin", qos=2)

    def stop(self):
        self.__running = False
        self.__status = "Stopped"
        self.boss.loop_stop()
        self.boss.disconnect()

    @property
    def status(self):
        return {"Status": self.__status, "Remaining Tasks": self.__queue.qsize(), "Uptime": round(time.time() - self.__time, 1)}

    @property
    def time(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    @property
    def management(self):
        return self.__management

    def addTask(self, *args):
        if not self.progressbar:
            print(self.time, "Task added")
        tasks = args[0]
        for task in tasks:
            self.__queue.put(task)
        self.__management["total_task"] = len(tasks)
        if self.progressbar:
            self.__pbar = tqdm(total=len(tasks), desc="TOTAL", smoothing=0)

    def removeTask(self):
        print("Task removed")
        with self.__queue.mutex:
            self.__queue.queue.clear()

    def onFinish(self, handler):
        self.__register("onFinish", handler)

    def onSingleResult(self, handler):
        self.__register("onSingleResult", handler)

    def loop_forever(self):
        self.__running = True
        self.__status = "Running"
        self.__time = time.time()
        # self.boss.connect("127.0.0.1")
        self.boss.connect("165.91.215.167")
        self.boss.subscribe("registration")
        self.boss.subscribe("feedback")
        self.boss.subscribe("heartbeat")
        self.boss.publish("broadcast", "fallin", qos=2)
        self.boss.loop_forever()



# def dynamic_load_balancing():
#     """
#     The function should be executed when start and every half minute, to determine the optimal task distribution to
#     minimize the total time cost. Based on each worker's performance, the calculated task remaining will be
#     signed/updated to each worker.
#     """
#     online_worker_list = []
#     performance_list = []
#     q_size = len(q)
#     for worker_name, child_dict in management.items():
#         if child_dict['status'] == 'online':
#             online_worker_list.append(worker_name)
#             performance_list.append(child_dict['performance'])
#     if 4*q_size > len(online_worker_list):
#         total_performance = sum(performance_list)
#         for name in online_worker_list:
#             management[name]['CRT'] = round(q_size*management[name]['performance']/total_performance+0.1)  #custom round
#
#
# def heartbeat_check():
#     if len(q) % (len(management)*2) == 0 and len(q):
#         boss.publish('broadcast', 'heartbeat')


# TODO
# 1. (X)Boss can be online anytime
# 2. (X)Multiple workers can be deployed easily
# 3. (X)Worker can be offline anytime without loss of task
# 4. Objectify the boss and worker scripts
# 5. (X)Enable the QoS 2 mode
# 6. Task progress feedback
# 7. Dynamic load balancing (optimize the total time cost)
# 8. (X)Boss can activate Always-Online mode: workers will not leave after work
# 9. (X)Worker can activate PhD mode: stay in the office while do nothing
# 10. Heartbeat feedback
# 11. Multiple BOSS/WORKER exist in the same broker
# 12. Initial computing power evaluation (from spec to score)
