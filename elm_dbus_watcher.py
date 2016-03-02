import argparse
import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import Gtk as gtk
import can
import json
from multiprocessing import Process, Queue

import can_dbc_reader

elm_name = "rvi.vsi.ElmDbus"
elm_path = "/rvi/vsi/ElmDbus/object"

import binascii

class ElmDbusCanWatcher(dbus.service.Object):

    def __init__(self, conn, object_path='/rvi/vsi/ElmDbusCanWatcher/object'):
        dbus.service.Object.__init__(self, conn, object_path)
        self.busName = dbus.service.BusName('rvi.vsi.ElmDbusCanWatcher',
                                            bus=dbus.SessionBus())

        self.raw_message_queue = Queue()
        self.interp_message_queue = Queue()

        self._interp = CanInterpreter()
        self._interp.interp_queue = self.interp_message_queue

        self.print_interp_thread = Process(target=self.print_interp_message, args=(True,))
        self.print_interp_thread.start()


    @dbus.service.signal('rvi.vsi.ElmDbusCanWatcher')
    def interpreted_can_signal(self, interpreted_message=None):
        print(interpreted_message)
        pass

    def CAN_signal_handler(self, can_message=None):
        self.CAN_handler(can_message)

    def CAN_handler(self, can_message=None):
        # print(can_message)
        self.raw_message_queue.put(can_message)
        self.create_can_message_from_raw_signal(self.raw_message_queue, self.interp_message_queue)

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

            can_data = []

            while(raw_list.__len__() > 0):
               can_data.append(int(raw_list.pop(), 16))

            can_data = bytearray(can_data)

            can_message.arbitration_id = can_id
            can_message.data = can_data

            # actually interpret the message...!
            self._interp.interp_message(can_message)
            #perhaps make the above blocking to ...

    def print_interp_message(self, exclusive=False):
        while(True):
            if (self.interp_message_queue.empty() == False):
                msg = self.interp_message_queue.get()
                self.interpreted_can_signal(msg)
                # print(msg)

class CanInterpreter(object):
    def __init__(self):
        object.__init__(self)
        self.interp_queue = None

        self.can_table = can_dbc_reader.get_can('utf8_can_dbc.txt')
        self.state_table = {}
        self.signal_table = {}

        for key in self.can_table:
            self.state_table[key] = None

        for arb_id, params in self.can_table.items():
            for signal, values in params['species'].items():
                self.signal_table[signal] = self.can_table[arb_id]['species'][signal]['value']

    # Magic code to create a bitmask of length
    # maximum length is actuall the maximum number of bits we can have in each frame, we default to an 8 byte frame
    def get_mask_ones(self, length, maximum=0xFFFFFFFFFFFFFFFF):
        b = maximum << length
        c = b & maximum
        return (c^maximum)

    def map_values(self, arb_id, payload):
        num_bits = self.can_table[arb_id]['frame_bytes'] * 8
        for signal, specs in self.can_table[arb_id]['species'].items():
            sig_value = ((payload >> (specs['end_bit']-specs['length']+1)  & (self.get_mask_ones(length=specs['length'], maximum = ((2**num_bits)-1)))) * specs['factor']) + specs['offset']
            if specs['value'] == sig_value:
                pass
            else:
                specs['value'] = sig_value
                self.signal_table[signal] = sig_value
                # send result to the que
                if self.interp_queue.full() is False:
                    self.interp_queue.put(json.dumps({'signal_type':'VEHICLE_SIGNAL', 'signal_id':signal, 'value':sig_value}))

    def interp_message(self, message):
        self._interp_message_threaded(message)

    def _interp_message_threaded(self, message):
        msgId = int(message.arbitration_id)
        data = int(binascii.hexlify(message.data), 16)
        if msgId not in self.can_table:
            print('!!! WARNING UNKNOWN CAN FRAME !!!')

        elif msgId not in self.state_table:
            self.state_table[msgId] = data
            self.map_values(arb_id = msgId, payload = data)

        elif message.data == self.state_table[msgId]:
            pass

        else:
            self.state_table[msgId] = data
            self.map_values(arb_id = msgId, payload = data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=('Provoke the Elm Dbus object '+elm_name))

    #parser.add_argument('-m', '--method', help='Method to invoke')
    #parser.add_argument('-a', '--args', help='Method args', nargs='*')

    parser.add_argument('-c', '--watch-can', help='Start an object that watches the CAN signals', action='store_true')
    #parser.add_argument('-s', '--signal', help='Signal to watch')

    args = parser.parse_args()

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()

    if args.watch_can:

        watcher = ElmDbusCanWatcher(bus)

        elm = bus.get_object(elm_name, elm_path)

        # elm.connect_to_signal('can_response', watcher.CAN_signal_handler,
        #                       dbus_interface=elm_name)

        # also connect to at responses for now
        elm.connect_to_signal('at_response', watcher.CAN_signal_handler,
                              dbus_interface=elm_name)

        monitor_can = elm.get_dbus_method('monitor_can', dbus_interface=elm_name)

        silent = False
        format = True
        header = True
        spaces = True

        #monitor_can(silent, format, header, spaces)

    print('Starting GTK Main')
    gtk.main()
