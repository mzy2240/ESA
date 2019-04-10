# -*- coding: utf-8 -*-
"""
Created on Tue Apr  9 09:50:15 2019

@author: yijin
"""
import paho.mqtt.client as mqtt
import plotly as py
import plotly.graph_objs as go
import sys
from ast import literal_eval

class progressbar:
    def __init__(self,ip="165.91.215.167",port=1883):
        self.ip = ip
        self.port = port
        self.client = mqtt.Client()
        self.client.on_connect = self.__on_connect
        self.client.on_message = self.__on_message
        self.client.connect(ip, port)
        
    def start(self):
        self.client.subscribe("dashboard")
        self.client.loop_forever()
    
    def __on_connect(self,client, userdata, flags, rc):
        print("Connected with Manager "+str(rc))
     
    def __on_message(self,client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))
        if 'dashboard' in msg.topic:
            done = literal_eval(msg.payload.decode())
            print(done)
      #      Done_task = 
            print(done['task_count'])
# =============================================================================
#             trace1 = go.Bar(
#                 y=['Progress Bar'],
#                 x=[12],
#                 name='Done',
#                 orientation = 'h',
#                 marker = dict(
#                     color = 'rgb(44, 160, 44)',
#                     line = dict(
#                         color = 'rgb(44, 160, 44)',
#                         width = 1)
#                 )
#             )
#             trace2 = go.Bar(
#                 y=['Progress Bar'],
#                 x=[28],
#                 name='Running',
#                 orientation = 'h',
#                 marker = dict(
#                     color = 'rgb(31, 119, 180)',
#                     line = dict(
#                         color = 'rgb(31, 119, 180)',
#                         width = 1)
#                 )
#             )   
#                 
#             trace3 = go.Bar(
#                 y=['Progress Bar'],
#                 x=[60],
#                 name='Progress Bar',
#                 orientation = 'h',
#                 marker = dict(
#                     color = 'rgb(255, 127, 14)',
#                     line = dict(
#                         color = 'rgb(255, 127, 14)',
#                         width = 1)
#                 )
#             )    
#             data = [trace1, trace2, trace3]
#             layout = go.Layout(
#                 barmode='stack'
#             )
#             fig = go.Figure(data=data, layout=layout)
#            # fig
#             py.offline.plot(fig, filename='marker-h-bar')                                
# =============================================================================
    def __close(self):
        self.client.disconnect()

        
    
    
# =============================================================================
# ProgressBar = mqtt.Client()
# ProgressBar.subscribe("dashboard")
# ProgressBar.subscribe("registration")
# =============================================================================
# =============================================================================
#     args = sys.argv
#     if len(args) == 1:
#         # ip = "127.0.0.1"
#         ip = "165.91.215.167"
#         port = 1883
#     elif len(args) == 2:
#         ip = args[1]
#         port = 1883
#     else:
#         ip = args[1]
#         port = int(args[2])
#         file_path = args[3]
#     client = mqtt.Client()
#     client.on_connect = on_connect
#     client.on_message = on_message
#     client.connect(ip, port)
# =============================================================================



    



    

