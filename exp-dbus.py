import argparse
import dbus
import dbus.mainloop.glib
import dbus.service
import threading
from gi.repository import Gtk as gtk

# from elm327.connection import *
# from elm327.obd import *

import serial
from serial import *

from connection import *
from obd import *

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--serial_device", help="Serial device to connect")
parser.add_argument("-b", "--baud_rate", help="Baud rate for communication",
                    type=int)
args = parser.parse_args()

SERIAL_DEVICE = args.serial_device
BAUD_RATE = args.baud_rate


# create test class for elm chip on dbus
class ElmDbus(dbus.service.Object):
    def __init__(self, conn, object_path='/rvi/vsi/ElmDbus/object'):
        dbus.service.Object.__init__(self, conn, object_path)
        self.busname = dbus.service.BusName('rvi.vsi.ElmDbus',
                                            bus=dbus.SessionBus())
        self.obd = None

    @dbus.service.signal('rvi.vsi.ElmDbus')
    def at_response(self, msg=None):
        # send the message string of the serial response from the elm
        print(msg)
        # return msg

    @dbus.service.method('rvi.vsi.ElmDbus')
    def at_send_raw(self, msg=None):
        print ">" + msg
        response = self.obd._send_command(str(msg))
        self.at_response(response)

def start_elm(ElmDbus, serial_device=None, baud_rate=0):
    if SERIAL_DEVICE:
        if BAUD_RATE >= 9600 and BAUD_RATE <= 1000000:

            ser = SerialConnectionFactory(port_class=Serial,
                                          baudrate=9600,
                                          parity=PARITY_NONE,
                                          timeout=0.5,
                                          write_timeout=0.1)

            connection = ser.connect(SERIAL_DEVICE)

            ElmDbus.obd = OBDInterface(connection)

            # print((obd._send_command("ATZ")))

            ElmDbus.at_response(ElmDbus.obd._send_command("ATI"))
            ElmDbus.at_response(ElmDbus.obd._send_command("ATE0"))
            ElmDbus.at_response(ElmDbus.obd._send_command("STSBR" + str(BAUD_RATE)))

            #close connection, reconnect
            ElmDbus.obd._connection.close()

            ser = SerialConnectionFactory(port_class=Serial,
                                          baudrate=BAUD_RATE,
                                          parity=PARITY_NONE,
                                          timeout=0.5,
                                          write_timeout=0.1)

            connection = ser.connect(SERIAL_DEVICE)

            ElmDbus.obd = OBDInterface(connection)

            ElmDbus.at_response(ElmDbus.obd._send_command("STI"))


        else:
            print("Baud rate incorrect. Supply range 9600:1000000")

    else:
        print("Insufficient args provided.\n"
              "Please supply serial device and baudrate\n")

def read_elm(ElmDbus):
    while(True):
        line = ElmDbus.obd._connection._read()
        if line:
            print(ElmDbus.at_response(line))

# main loop run dbus object for elm
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    # create dbus object
    elm_obj = ElmDbus(dbus.SessionBus())

    # start thread on func
    # elm_thread_start = threading.Thread(target=start_elm,
    #                               args=(elm_obj, SERIAL_DEVICE, BAUD_RATE))
    # elm_thread_start.start()

    # blocking setup call to start elm chip for the first time
    start_elm(elm_obj, SERIAL_DEVICE, BAUD_RATE)

    #we assume elm has started and we can talk to it...

    #set up for can monitor
    print(elm_obj.at_response(elm_obj.obd._send_command("ath1")))
    print(elm_obj.at_response(elm_obj.obd._send_command("atcsm0")))

    elm_thread_read = threading.Thread(target=read_elm, args=(elm_obj,))
    elm_thread_read.start()

    print('Starting GTK Main')
    gtk.main()
