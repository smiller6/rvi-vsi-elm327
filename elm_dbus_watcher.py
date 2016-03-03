import argparse
import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import Gtk as gtk
import can
import json
from multiprocessing import Process, Queue
import struct
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

    def return_shift_endian(self, num_bytes=0, value=0 ):
        assert num_bytes >= 0
        mask = 255
        r_val = ((value << (num_bytes * 8)) & (mask << (num_bytes * 8)))
        if num_bytes > 0:
                r_val |= self.return_shift_endian(num_bytes=num_bytes-1, value=value)
        return r_val

    def swap_bytes(self, num, size_bytes=2):
        assert size_bytes <= 8
        if size_bytes == 2:
            #treat as short
            return struct.unpack('<H', struct.pack('>H', num))[0]
        elif 2 < size_bytes <= 4:
            # int
            return struct.unpack('<I', struct.pack('>I', num))[0]
        elif 4 < size_bytes <= 8:
            # long
            return struct.unpack('<L', struct.pack('>L', num))[0]

    def map_values(self, arb_id, payload):
        num_bits = self.can_table[arb_id]['frame_bytes'] * 8
        for signal, specs in self.can_table[arb_id]['species'].items():
            # discovered that the database stores entries for values greater than
            # one byte in a strange format that defies out easy shift operation
            # [end_bit] - [length] + 1 will always get you the right operation
            # as long as end bit is greater than the length...
            # but there are entries like this: 15 | 16 or 17 | 10  (!)
            # so: the end bit still applies. but since a multi byte value is stored
            # flipped (ie 3FE gets packed in as FE03), then the end bit designates
            # the correct end for that number, but we have to assume that the
            # next byte entire is used for the value as well
            # SO! our formula changes if the length of the value is greater than a byte

            sig_length = specs['length']
            sig_end = specs['end_bit']
            # old style works well for single byte...
            if sig_length <= 8:
                sig_value = ((payload >> (sig_end - sig_length + 1)  & (self.get_mask_ones(length=sig_length, maximum = ((2**num_bits)-1)))) * specs['factor']) + specs['offset']
            elif sig_length > 8:
                # need a new shiftby, because the endbit is on the end of a byte closer to the right...
                index = sig_end
                # local copy of payload for isolation and manipulation
                data = payload
                # while index does not point to somewhere in the rightmost byte,
                # shift by 8
                while index > 7:
                    data >>= 8
                    index -= 8
                # # our two bytes should be on the right, so mask, flip and find the value...
                # just how many bytes does our value take up?
                byte_val = sig_length // 8
                # create a mask using the position of the first relevant byte
                mask = data & (0xFFFFFFFFFFFFFFFF >> (sig_end -  (sig_length - 8) + 1))
                data &= mask
                sig_value = self.swap_bytes(data, size_bytes= byte_val)

                sig_value = (sig_value * specs['factor']) + specs['offset']

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
