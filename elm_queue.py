
from multiprocessing import Queue
# import Queue

# Python module for using an elm327/stn1110 via serial connection, supporting
# interaction over dbus. We want to have a dbus object that takes requests
# and passes the arguments to the serial connection, using a queue. For every
# command, there should be a response...

COMMAND_QUEUE_MAX_SIZE = 1024

RESPONSE_QUEUE_MAX_SIZE = 1024

# class CommandQueue(Queue):
#     def __init__(self, COMMAND_QUEUE_MAX_SIZE):
#         Queue.__init__(self, COMMAND_QUEUE_MAX_SIZE)
#
# def send_command(CommandQueue, command):
#     CommandQueue.put(command)
#
# def get_command(CommandQueue):
#     return CommandQueue.get()
#
#
# class ResponseQueue(Queue):
#     def __init__(self, RESPONSE_QUEUE_MAX_SIZE):
#         Queue.__init__(self, RESPONSE_QUEUE_MAX_SIZE)
#
# def send_response(ResponseQueue, command):
#     ResponseQueue.put(command)
#
# def get_response(ResponseQueue):
#     return ResponseQueue.get()

