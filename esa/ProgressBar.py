import paho.mqtt.client as mqtt
import plotly.graph_objs as go
import plotly
from ast import literal_eval



# init_notebook_mode(connected=True)


class progressbar:
    def __init__(self, ip="165.91.215.167", port=1883):
        print("ProgressBar initialized")
        self.ip = ip
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.__on_connect
        print("Connection finished")
        self.client.on_message = self.__on_message
        print("Plotting initialized")
        self.client.connect(ip, port)
        self._plot_initialize()

    def _plot_initialize(self):
        total_count = 0
        total_ongoing_count = 0
        task_left = 0
        n_worker = 0
        trace_sub1 = []
        worker_efficiency = []
        worker_id = []
        trace1 = go.Bar(
            y=['ProgressBar'],
            x=[total_count],
            name='Done_task',
            orientation='h',
            marker=dict(
                color='rgb(44, 160, 44)',
                line=dict(
                    color='rgb(44, 160, 44)',
                    width=0.8)
            )
        )
        trace2 = go.Bar(
            y=['ProgressBar'],
            x=[total_ongoing_count],
            name='Running task',
            orientation='h',
            marker=dict(
                color='rgb(31, 119, 180)',
                line=dict(
                    color='rgb(31, 119, 180)',
                    width=0.8)
            )
        )

        trace3 = go.Bar(
            y=['ProgressBar'],
            x=[task_left],
            name='Left task',
            orientation='h',
            marker=dict(
                color='rgb(255, 127, 14)',
                line=dict(
                    color='rgb(255, 127, 14)',
                    width=0.8)
            )
        )
        print('number of worker:', n_worker)
        print('worker_efficiency=', worker_efficiency[:])
        trace4 = go.Bar(
            x=worker_efficiency[:],
            # x = [1,2,3],
            y=worker_id[:],
            name='Worker efficiency',
            orientation='h'
        )
        fig = plotly.tools.make_subplots(rows=1, cols=2)
        fig.append_trace(trace1, 1, 1)
        fig.append_trace(trace2, 1, 1)
        fig.append_trace(trace3, 1, 1)
        print(trace_sub1)
        print(worker_efficiency)
        fig.append_trace(trace4, 1, 2)
        fig.layout.update(go.Layout(barmode='stack', ))
        self.fig = go.FigureWidget(fig)

    @property
    def figure(self):
        return self.fig

    def start(self):
        self.client.loop_forever()

    def __on_connect(self, client, userdata, flags, rc):
        print("Connected with Manager " + str(rc))
        self.client.subscribe("dashboard")
        print("Already subscribed dashboard")
        # return True

    def __on_message(self, client, userdata, msg):
        print("I'm editing the PB file")
        #    print(msg.topic+" "+msg.payload.decode())
        if 'dashboard' in msg.topic:
            print("start")
            done = literal_eval(msg.payload.decode())
            #        print("keys: ", done.keys())
            total_finished = []
            total_ongoing = []
            mat_plot = []
            worker_efficiency = []
            worker_id = []
            total_task = done['total_task']
            print("total_task: ", total_task)
            n_worker = 0
            for worker in list(done.keys())[1:]:
                n_worker += 1
                worker_id.append(worker)
                total_finished.append(done[worker]['task_count'])
                if done[worker]['efficiency'] is None:
                    worker_efficiency.append(0)
                else:
                    worker_efficiency.append(done[worker]['efficiency'])
                if done[worker]['task'] is not None:
                    total_ongoing.append(done[worker]['task'])
            # print(n_worker)
            # print(worker_efficiency)
            print(worker_id)
            total_ongoing_count = len(total_ongoing)
            total_count = sum(total_finished)
            #             print("total_count(Done):", total_count)
            #             print("total_ongoing_count(Running)", total_ongoing_count)
            task_left = total_task - total_count - total_ongoing_count
            #             print("total_count(Left):", task_left)
            # New Method sart here
            #             mat_plot.append
            print(self.fig.data)
            self.fig.data[0].x = [total_count]
            self.fig.data[1].x = [total_ongoing_count]
            self.fig.data[2].x = [task_left]
            # for i in range(n_worker):
            self.fig.data[3].y = worker_id[:]
            self.fig.data[3].x = worker_efficiency[:]

    def __close(self):
        self.client.disconnect()

