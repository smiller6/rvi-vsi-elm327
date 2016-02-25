import argparse
import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import Gtk as gtk
from collections import deque
import Queue
import threading
#please run this with python3
import can
import time
import json
import can_dbc_reader

elm_name = "rvi.vsi.ElmDbus"
elm_path = "/rvi/vsi/ElmDbus/object"


parser = argparse.ArgumentParser(description=('Provoke the Elm Dbus object '+elm_name))

#parser.add_argument('-m', '--method', help='Method to invoke')
#parser.add_argument('-a', '--args', help='Method args', nargs='*')

parser.add_argument('-c', '--watch-can', help='Start an object that watches the CAN signals', action='store_true')
#parser.add_argument('-s', '--signal', help='Signal to watch')

args = parser.parse_args()

# method = args.method
# nargs = args.args

class ElmDbusCanWatcher(dbus.service.Object):

    def __init__(self, conn, object_path='/rvi/vsi/ElmDbusCanWatcher/object'):
        dbus.service.Object.__init__(self, conn, object_path)

        # store of messages to be parsed
        self.messages = deque()

        self.raw_message_queue = Queue.Queue()
        self.interp_message_queue = Queue.Queue()

    def CAN_signal_handler(self, can_message=None):
        #print(can_message)
        self.raw_message_queue.put(can_message)
        interp_thread = threading.Thread(target=self.create_can_message_from_raw_signal,
                         args=(self.raw_message_queue,
                               self.interp_message_queue))
        interp_thread.start()
        interp_thread.join()

    def create_can_message_from_raw_signal(self, raw_queue, interp_queue):
        # can_message = can.Message(timestamp=0.0,
        #                           is_remote_frame=False,
        #                           is_error_frame=False,
        #                           arbitration_id=0,
        #                           dlc=None,
        #                           data=None
        #                           )
        can_message = can.Message()

        # parse the string for the id. the rest should be data
        if (raw_queue.empty() is False):
            raw = raw_queue.get()

            converted = raw.encode('utf-8')

            raw_list = list()
            raw_list = converted.split()

            can_id = int(raw_list.pop(0), 16)

            can_data = str()

            while(raw_list.__len__() > 0):
                can_data += raw_list.pop(0)

            # should be done using the raw queue
            raw_queue.task_done()

            can_data = bytearray(can_data)

            can_message.arbitration_id = can_id
            can_message.data = can_data

            # test print result
            #print(can_message)

            # TODO: actually interpret the message...!

        if (interp_queue.full() is False):
            interp_queue.put(can_message)

    def interp_message(self, message):
        pass

    # test function, use this if not getting the interp message for signal emission
    def print_interp_message(self, exclusive=False):
        while(True):
            if (self.interp_message_queue.empty() == False):
                msg = self.interp_message_queue.get()
                print(msg)
                # only set task done if this is exclusive...
                if exclusive is True:
                    self.interp_message_queue.task_done()

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()

    if args.watch_can:

        watcher = ElmDbusCanWatcher(bus)

        elm = bus.get_object(elm_name, elm_path)

        elm.connect_to_signal('can_response', watcher.CAN_signal_handler,
                              dbus_interface=elm_name)

        # also connect to at responses for now
        elm.connect_to_signal('at_response', watcher.CAN_signal_handler,
                              dbus_interface=elm_name)

        monitor_can = elm.get_dbus_method('monitor_can', dbus_interface=elm_name)

        silent = False
        format = True
        header = True
        spaces = True

        #monitor_can(silent, format, header, spaces)

        # for now, please print the interpretations locally
        print_interp_thread = threading.Thread(target=watcher.print_interp_message, args=(False,))
        print_interp_thread.start()

    gtk.main()
