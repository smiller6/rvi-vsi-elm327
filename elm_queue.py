
from multiprocessing import Process
import Queue

# Python module for using an elm327/stn1110 via serial connection, supporting
# interaction over dbus. We want to have a dbus object that takes requests
# and passes the arguments to the serial connection, using a queue. For every
# command, there should be a response...

COMMAND_QUEUE_MAX_SIZE = 1024

RESPONSE_QUEUE_MAX_SIZE = 1024

class CommandQueue(Queue.Queue):
    def __init__(self, maxSize=0):
        Queue.Queue.__init__(self, maxSize)

def send_command(CommandQueue, command):
    CommandQueue.put(command)

def get_command(CommandQueue):
    return CommandQueue.get()


class ResponseQueue(Queue.Queue):
    def __init__(self, maxSize=0):
        Queue.Queue.__init__(self, maxSize)

def send_response(ResponseQueue, command):
    ResponseQueue.put(command)

def get_response(ResponseQueue):
    return ResponseQueue.get()

