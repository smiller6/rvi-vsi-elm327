import argparse
import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import Gtk as gtk
from collections import deque

#please run this with python3
import can

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

    def CAN_signal_handler(self, can_message=None):
        #print(can_message)
        print(self.create_can_message_from_raw_signal(can_message))

    def create_can_message_from_raw_signal(self, raw=None):
        # can_message = can.Message(timestamp=0.0,
        #                           is_remote_frame=False,
        #                           is_error_frame=False,
        #                           arbitration_id=0,
        #                           dlc=None,
        #                           data=None
        #                           )
        can_message = can.Message()

        # parse the string for the id. the rest should be data

        converted = raw.encode('utf-8')

        raw_list = list()
        raw_list = converted.split()

        can_id = int(raw_list.pop(0), 16)

        can_data = str()

        while(raw_list.__len__() > 0):
            can_data += raw_list.pop(0)

        can_data = bytearray(can_data)

        can_message.arbitration_id = can_id
        can_message.data = can_data

        # test print result
        print(can_message)

        return can_message


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

    gtk.main()
