#note to user:
# for this to work the following should be installed:
#   apt-packages:
#       gir1.2-gtk-3.0
#       gobject-introspection
#       python-gi
#    python:
#        pyserial

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

    ############################################################################
    #   dbus

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

    @dbus.service.signal('rvi.vsi.ElmDbus')
    def can_response(self, msg=None):
        print(msg)

    @dbus.service.method('rvi.vsi.ElmDbus')
    def monitor_can(self, silent=False, format=True, header=True, spaces=True):

        #set parameters desired for can output
        self.command_set_silent_monitor(silent)
        self.command_format_can(format)
        self.command_header_on(header)
        self.command_spaces_on(spaces)
        self.command_monitor_can_at()

        #this line is problematic, we need a way to start monitoring/reading
        #without blocking the reply
        read_elm(self)
        return 'Starting can monitor'
    ############################################################################

    ############################################################################
    #commands
    #   commands for interacting directly with ELM/STN chip
    #   ST specific commands are designated with the postfix _st
    #   per the ELM/STN set, most commands take a single argument

    def command_set_silent_monitor(self, silent=True):
        if silent:
            return self.obd._send_command("ATCSM1")
        else:
            return self.obd._send_command("ATCSM0")

    def command_format_can(self, format=True):
        if format:
            return self.obd._send_command("ATCAF1")
        else:
            return self.obd._send_command("ATCAF0")

    def command_header_on(self, header=True):
        if header:
            return self.obd._send_command("ATH1")
        else:
            return self.obd._send_command("ATH0")

    def command_spaces_on(self, spaces=True):
        if spaces:
            return self.obd._send_command("ATS1")
        else:
            return self.obd._send_command("ATS0")

    def command_set_baud_rate_st(self, rate=9600):
        if rate >= 9600 and rate <= 2000000:
            return self.obd._send_command("STSBR" + str(rate))
        else:
            return False

    def command_echo_on(self, echo=True):
        if echo:
            return self.obd._send_command("ATE1")
        else:
            return self.obd._send_command("ATE0")

    def command_monitor_can_at(self):
        return self.obd._send_command("ATMA")

    def command_select_protocol(self, protocol_number="0"):
        return self.obd._send_command("ATSP" + protocol_number)

    def command_select_protocol_auto(self, protocol_number="0"):
        return self.obd._send_command("ATSPA" + protocol_number)


    ############################################################################
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


    # blocking setup call to start elm chip for the first time
    start_elm(elm_obj, SERIAL_DEVICE, BAUD_RATE)

    #we assume elm has started and we can talk to it...

    # set up for can monitor


    print(elm_obj.at_response(elm_obj.obd._send_command("ath1")))
    #this line is only because we know what rate we are looking for on can
    print(elm_obj.at_response(elm_obj.obd._send_command("atspa8")))
    print(elm_obj.at_response(elm_obj.obd._send_command("atcaf0")))
    print(elm_obj.at_response(elm_obj.obd._send_command("atcsm0")))
    print(elm_obj.at_response(elm_obj.obd._send_command("atma")))

    elm_thread_read = threading.Thread(target=read_elm, args=(elm_obj,))
    elm_thread_read.start()


    #elm_obj.monitor_can(silent=False, format=True, header=True, spaces=True)

    print('Starting GTK Main')
    gtk.main()
