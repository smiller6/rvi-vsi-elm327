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

from serial import *

from connection import *
from obd import *

from elm_queue import *

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--serial_device", help="Serial device to connect")
parser.add_argument("-b", "--baud_rate", help="Baud rate for communication",
                    type=int)
args = parser.parse_args()

SERIAL_DEVICE = args.serial_device
BAUD_RATE = args.baud_rate


command_queue = CommandQueue(maxSize=COMMAND_QUEUE_MAX_SIZE)
response_queue = ResponseQueue(maxSize=RESPONSE_QUEUE_MAX_SIZE)

# create test class for elm chip on dbus
class ElmDbus(dbus.service.Object):

    def __init__(self, conn, object_path='/rvi/vsi/ElmDbus/object'):
        dbus.service.Object.__init__(self, conn, object_path)
        self.busname = dbus.service.BusName('rvi.vsi.ElmDbus',
                                            bus=dbus.SessionBus())
        self.obd = None

        self._command_queue = command_queue
        self._response_queue = response_queue

    ############################################################################
    #   dbus

    @dbus.service.signal('rvi.vsi.ElmDbus')
    def at_response(self, msg=None):
        # send the message string of the serial response from the elm
        print(msg)
        # return msg

    @dbus.service.method('rvi.vsi.ElmDbus')
    def at_command(self, msg=None):
        print ">" + msg
        self._command_que.put(msg)

    @dbus.service.signal('rvi.vsi.ElmDbus')
    def can_response(self, msg=None):
        print(msg)

    @dbus.service.method('rvi.vsi.ElmDbus')
    def monitor_can(self, silent=False, format_can=True, header=True,
                    spaces=True):
        self._command_queue.put('ath1')
        self._command_queue.put('atspa8')
        self._command_queue.put('atcaf0')
        self._command_queue.put('atcsm0')
        self._command_queue.put('atdp')
        self._command_queue.put('atma')

        #this line is problematic, we need a way to start monitoring/reading
        #without blocking the reply
        #read_elm(self)
        reply = 'Sending commands to monitor CAN, ' \
                'silent={silent}, ' \
                'format_can={format_can}' \
                'header={header}' \
                'spaces={spaces}'.format(silent=silent, format_can=format_can,
                                         header=header, spaces=spaces)
        print(reply)
        return reply


################################################################################


################################################################################
class ElmObd(object):
    def __init__(self, command_queue, response_queue):
        object.__init__(self)

        self.obd = None
        self._command_queue = command_queue
        self._response_queue = response_queue
        self.response = None
    #commands
    #   commands for interacting directly with ELM/STN chip
    #   ST specific commands are designated with the postfix _st
    #   per the ELM/STN set, most commands take a single argument

    def command_at_command(self, command=""):
        return self.obd._send_command(command)

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

    def start_elm(self, serial_device=None, baud_rate=0):
        if SERIAL_DEVICE:
            if BAUD_RATE >= 9600 and BAUD_RATE <= 1000000:

                ser = SerialConnectionFactory(port_class=Serial,
                                              baudrate=9600,
                                              parity=PARITY_NONE,
                                              timeout=0.5,
                                              write_timeout=0.1)

                connection = ser.connect(SERIAL_DEVICE)

                self.obd = OBDInterface(connection)

                self._response_queue.put(self.command_at_command("ATI"))
                self._response_queue.put(self.command_at_command("ATE0"))
                self._response_queue.put(
                    self.command_at_command("STSBR" + str(BAUD_RATE)))

                # close connection, reconnect
                self.obd._connection.close()

                ser = SerialConnectionFactory(port_class=Serial,
                                              baudrate=BAUD_RATE,
                                              parity=PARITY_NONE,
                                              timeout=0.5,
                                              write_timeout=0.1)

                connection = ser.connect(SERIAL_DEVICE)

                self.obd = OBDInterface(connection)
                response = self.command_at_command("STI")
                response_queue.put(response)


            else:
                print("Baud rate incorrect. Supply range 9600:1000000")

        else:
            print("Insufficient args provided.\n"
                  "Please supply serial device and baudrate\n")


################################################################################


# def read_elm(ElmDbus):
#     while(True):
#         line = ElmObd.obd._connection._read()
#         if line:
#             print(ElmDbus.at_response(line))

def run_elm_obd(ElmObd):
    # if there's a command in the command que, send the command to serial
    # if no command, just read the serial and put that in the response que
    while(True):
        elm_response = None

        if (command_queue.empty() == False):
            command = command_queue.get()
            elm_response = ElmObd.obd._send_command(command)
            command_queue.task_done()
        else:
            elm_response = ElmObd.obd._connection._read()

        # we don't care about responses that have no info
        if elm_response is not None and elm_response is not '':
            response_queue.put(elm_response)
            

def run_dbus(ElmDbus):
    while(True):
        if (response_queue.empty() == False):
            #publish response
            response = response_queue.get()
            ElmDbus.at_response(response)
            response_queue.task_done()

# main loop run dbus object for elm
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    # create dbus object
    elm_dbus = ElmDbus(dbus.SessionBus())
    elm_obd = ElmObd(command_queue, response_queue)
    # start thread on func

    # blocking setup call to start elm chip for the first time
    elm_obd.start_elm(SERIAL_DEVICE, BAUD_RATE)

    # we assume elm has started and we can talk to it...

    # example/test of command response:
    send_command(command_queue, "atws")
    command = command_queue.get()
    command_queue.task_done()
    print(elm_obd.obd._send_command(command))
    response = elm_obd.obd._connection._read()
    response_queue.put(response)
    elm_dbus.at_response(response_queue.get())
    response_queue.task_done()

    elm_thread = threading.Thread(target=run_elm_obd, args=(elm_obd,))
    elm_dbus_thread = threading.Thread(target=run_dbus, args=(elm_dbus,))

    elm_thread.start()
    elm_dbus_thread.start()

    # elm_dbus.monitor_can(silent=False, format_can=True, header=True, spaces=True)

    print('Starting GTK Main')
    gtk.main()
