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
from dbus.mainloop.glib import DBusGMainLoop
import dbus.service
from multiprocessing import Process, Queue

from serial import *

from connection import *
from obd import *

from elm_dbus_watcher import ElmDbusCanWatcher, CanInterpreter

COMMAND_QUEUE_MAX_SIZE = 1024

RESPONSE_QUEUE_MAX_SIZE = 1024

EXPECTED_STI_VERSION = 'STN1110 v3.2.0'

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--serial_device", help="Serial device to connect")
parser.add_argument("-b", "--baud_rate", help="Baud rate for serial communication",
                    type=int)
parser.add_argument("--can_auto_start", help="Start can monitoring automatically",
                    action='store_true')
parser.add_argument("--can_silent", help="CAN Silent Monitoring Disable",
                    action='store_true')
# parser.add_argument("-r", "--can_rate", help="CAN communication rate (kbps)",
#                     type=int)
parser.add_argument("--can_protocol",
                    help="CAN Protocol:\n"
                    "0 Automatic\n"
                    "1 SAE J1850 PWM (41.6 Kbaud)\n"
                    "2 SAE J1850 VPW (10.4 Kbaud)\n"
                    "3 ISO 9141-2 (5 baud init)\n"
                    "4 ISO 14230-4 KWP (5 baud init)\n"
                    "5 ISO 14230-4 KWP (fast init)\n"
                    "6 ISO 15765-4 CAN (11 bit ID, 500 Kbaud)\n"
                    "7 ISO 15765-4 CAN (29 bit ID, 500 Kbaud)\n"
                    "8 ISO 15765-4 CAN (11 bit ID, 250 Kbaud)\n"
                    "9 ISO 15765-4 CAN (29 bit ID, 250 Kbaud)\n"
                    "A SAE J1939 CAN (29 bit ID, 250* Kbaud)\n"
                    "B User1 CAN (11 bit ID, 125 Kbaud)(programmable)\n",
                    default="0"
                    )
parser.add_argument("--custom_can_rate",
                    help="If using protocol other than one "
                    "of the defaults, use this option "
                    "to set a custom CAN rate of up to "
                    "500kbps",
                    default=125000
                    )
parser.add_argument("--interpret_can",
                    help="Can database path",
                    default="utf8_can_dbc.txt")
args = parser.parse_args()

SERIAL_DEVICE = args.serial_device
BAUD_RATE = args.baud_rate
CAN_AUTO_START = args.can_auto_start
CAN_SILENT_MONITORING = args.can_silent
CAN_PROTOCOL = str(args.can_protocol)
CUSTOM_CAN_RATE = args.custom_can_rate
CANDB_PATH = str(args.interpret_can)

command_queue = Queue(COMMAND_QUEUE_MAX_SIZE)
response_queue = Queue(RESPONSE_QUEUE_MAX_SIZE)

class ElmRepsonse():
    def __init__(self, msg=None, msg_type=None):
        # msg holds the actual message string from ELM
        self.msg = msg
        #msgTypes:
        # 'at'
        # 'can'
        # 'obd'
        self.msg_type = msg_type


# create test class for elm chip on dbus
class ElmDbus(dbus.service.Object):

    def __init__(self, conn, object_path='/rvi/vsi/ElmDbus/object'):
        dbus.service.Object.__init__(self, conn, object_path)
        self.busname = dbus.service.BusName('rvi.vsi.ElmDbus',
                                            bus=dbus.SessionBus())
        # elm obd reference
        self._elm_obd = None

        self._command_queue = command_queue
        self._response_queue = response_queue

        self.bEmitRawCan = False
        self.bEmitInterpCan = True

        # start watcher and interpreter
        self.watcher = ElmDbusCanWatcher(conn)
        if CANDB_PATH is not None:
            self.watcher._interp.set_interpreter_path(db_path=CANDB_PATH)

    ############################################################################
    # dbus
    @dbus.service.method('rvi.vsi.ElmDbus')
    def at_command(self, msg=None):
        print ">" + msg
        self._command_que.put(msg)

    @dbus.service.signal('rvi.vsi.ElmDbus')
    def at_response(self, msg=None):
        # send the message string of the serial response from the elm
        print(msg)
        # return msg

    def emit_at_response(self, msg=None):
        try:
            msg.decode('utf-8')
            self.at_response(msg)
        except:
            print(msg)
        else:
            self.at_response("String not UTF8")

    @dbus.service.signal('rvi.vsi.ElmDbus')
    def can_response(self, msg=None):
        print(msg)

    @dbus.service.method('rvi.vsi.ElmDbus')
    def monitor_can(self, silent=True, format_can=False, header=True,
                    spaces=True):
        self.command_warm_start()
        self.command_echo_on(False)
        self.command_set_silent_monitor(silent)
        self.command_format_can(format_can)
        self.command_header_on(header)
        self.command_spaces_on(spaces)
        self.command_buffer_dump()
        self.command_monitor_can_at()

        #this line is problematic, we need a way to start monitoring/reading
        #without blocking the reply
        #read_elm(self)
        reply = 'Sending commands to monitor CAN, ' \
                'silent={silent}, ' \
                'format_can={format_can}, ' \
                'header={header}, ' \
                'spaces={spaces}'.format(silent=silent, format_can=format_can,
                                         header=header, spaces=spaces)
        print(reply)
        return reply

    @dbus.service.method('rvi.vsi.ElmDbus')
    def enable_signal_raw_can(self, enable=False):
        self.bEmitRawCan = enable

    @dbus.service.method('rvi.vsi.ElmDbus')
    def enable_signal_interp_can(self, enable=True):
        self.bEmitInterpCan = enable

    # DIRECT ELM COMMANDS
    # sends command to the queue
    def _send_command(self, command):
        self._command_queue.put(command)
    # This looks crazy, but the interface for the dbus looks the same as the obd
    # these should be exposed to dbus as the preferred way of sending the commands
    # rather than the at_command method
    def command_at_command(self, command=""):
        self._send_command(command)

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_buffer_dump(self):
        self._send_command("ATBD")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_set_silent_monitor(self, silent=True):
        if silent:
            self._send_command("ATCSM1")
        else:
            self._send_command("ATCSM0")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_format_can(self, format=True):
        if format:
            self._send_command("ATCAF1")
        else:
            self._send_command("ATCAF0")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_header_on(self, header=True):
        if header:
            self._send_command("ATH1")
        else:
            self._send_command("ATH0")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_spaces_on(self, spaces=True):
        if spaces:
            self._send_command("ATS1")
        else:
            self._send_command("ATS0")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_set_baud_rate_st(self, rate=9600):
        if rate >= 9600 and rate <= 2000000:
            self._send_command("STSBR" + str(rate))
        else:
            return False

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_echo_on(self, echo=True):
        if echo:
            self._send_command("ATE1")
        else:
            self._send_command("ATE0")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_monitor_can_at(self):
        self._send_command("ATMA")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_select_protocol(self, protocol_number="0"):
        self._send_command("ATSP" + protocol_number)

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_select_protocol_auto(self, protocol_number="0"):
        self._send_command("ATSPA" + protocol_number)

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_set_defaults(self):
        self._send_command("ATD")

    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_warm_start(self):
        self._send_command("ATWS")

    # full reset of chip, clears memory. all settings must be reprogrammed after
    @dbus.service.method('rvi.vsi.ElmDbus')
    def command_restart(self):
        self._send_command("\r")
        self._send_command("ATZ")
        if(self._elm_obd):
            self._elm_obd.obd._connection.close()
            self._elm_obd.start_elm(SERIAL_DEVICE, BAUD_RATE)

    @dbus.service.method('rvi.vsi.ElmDbus')
    def set_custom_can_rate(self, rate):
        _rate = int(rate)
        if(rate > 0 and rate <= 500000):
            # calc the divisor for the desired rate agains 500000
            div = int(500000/rate)
            div = str(hex(div))
            # program the programmable value for user can rate divisor
            self.command_at_command("AT" + "PP" + "2D" + "SV" + div)
################################################################################


################################################################################
class ElmObd(object):
    def __init__(self):
        object.__init__(self)

        self.obd = None
        self._command_queue = command_queue
        self._response_queue = response_queue
        
        # used to determine if we are still emitting frames
        self.last_command = ""
    #commands
    #   commands for interacting directly with ELM/STN chip
    #   ST specific commands are designated with the postfix _st
    #   per the ELM/STN set, most commands take a single argument

    def command_at_command(self, command=""):
        self.last_command = command
        return self.obd._send_command(str(command))

    def command_buffer_dump(self):
        return self.command_at_command("ATBD")

    def command_set_silent_monitor(self, silent=True):
        if silent:
            return self.command_at_command("ATCSM1")
        else:
            return self.command_at_command("ATCSM0")

    def command_format_can(self, format=True):
        if format:
            return self.command_at_command("ATCAF1")
        else:
            return self.command_at_command("ATCAF0")

    def command_header_on(self, header=True):
        if header:
            return self.command_at_command("ATH1")
        else:
            return self.command_at_command("ATH0")

    def command_spaces_on(self, spaces=True):
        if spaces:
            return self.command_at_command("ATS1")
        else:
            return self.command_at_command("ATS0")

    def command_set_baud_rate_st(self, rate=9600):
        if 9600 <= rate <= 2000000:
            return self.command_at_command("STSBR" + str(rate))
        else:
            return False

    def command_echo_on(self, echo=True):
        if echo:
            return self.command_at_command("ATE1")
        else:
            return self.command_at_command("ATE0")

    def command_monitor_can_at(self):
        return self.command_at_command("ATMA")

    def command_select_protocol(self, protocol_number="0"):
        return self.command_at_command("ATSP" + protocol_number)

    def command_select_protocol_auto(self, protocol_number="0"):
        return self.command_at_command("ATSPA" + protocol_number)

    def command_warm_start(self):
        return self.command_at_command("ATWS")

    def set_custom_can_rate(self, rate):
        _rate = int(rate)
        if(rate > 0 and rate <= 500000):
            # calc the divisor for the desired rate agains 500000
            div = int(500000/rate)
            div = str(hex(div))
            # program the programmable value for user can rate divisor
            self.command_at_command("AT" + "PP" + "2D" + "SV" + div)
    def send_response(self, msg=None, msg_type='at'):
        elm_response = ElmRepsonse(msg, msg_type)
        self._response_queue.put(elm_response)

    def start_elm(self, serial_device=None, baud_rate=0):
        if SERIAL_DEVICE:
            if BAUD_RATE >= 9600 and BAUD_RATE <= 1000000:

                self.baud_rate = baud_rate

                ser = SerialConnectionFactory(port_class=Serial,
                                              baudrate=9600,
                                              parity=PARITY_NONE,
                                              timeout=1,
                                              write_timeout=1)

                connection = ser.connect(SERIAL_DEVICE)

                time.sleep(1)

                self.obd = OBDInterface(connection)
                ati_response = self.command_at_command("ATI")
                #self._response_queue.put(ati_response)
                self.send_response(msg=ati_response)
                print("Low speed ATI response: " + ati_response)
                # self._response_queue.put(self.command_at_command("ATE0"))
                self.send_response(self.command_at_command("ATE0"))
                # self._response_queue.put(self.command_at_command("STSBR" + str(self.baud_rate)))
                self.send_response(self.command_at_command("STSBR" + str(self.baud_rate)))

                # close connection, reconnect
                self.obd._connection.close()
                time.sleep(1)
                ser = SerialConnectionFactory(port_class=Serial,
                                              baudrate=BAUD_RATE,
                                              parity=PARITY_NONE,
                                              timeout=3,
                                              write_timeout=1)

                connection = ser.connect(SERIAL_DEVICE)

                time.sleep(1)

                self.obd = OBDInterface(connection)
                # send a carriage return
                #print(self.obd._send_command("\r\r"))
                sti_response = self.command_at_command("STI")
                print("Desired Baud Rate STI response: " + sti_response)

                if CUSTOM_CAN_RATE:
                    self.set_custom_can_rate(CUSTOM_CAN_RATE)

                    # tell the elm to automatically select a protocol...
                self.command_select_protocol_auto(protocol_number=CAN_PROTOCOL)


                # cheat for now, we need a way to reliably test the response from the elm...
                return 0

            else:
                print("Baud rate incorrect. Supply range 9600:1000000")

        else:
            print("Insufficient args provided.\n"
                  "Please supply serial device and baudrate\n")


################################################################################

def run_elm_obd(ElmObd):
    # if there's a command in the command que, send the command to serial
    # if no command, just read the serial and put that in the response que
    while(True):
        elm_response = None

        if (command_queue.empty() == False):
            command = command_queue.get()
            # elm_response = ElmRepsonse(ElmObd.obd._send_command(command))
            # command_queue.task_done()
            elm_response = ElmObd.command_at_command(command)
        else:
            # elm_response = ElmRepsonse(ElmObd.obd._send_command())
            elm_response = ElmObd.obd._send_command(None)

        # we don't care about responses that have no info
        if elm_response is not None and elm_response is not '':
            if (ElmObd.last_command).lower() == 'atma':
                # elm_response.msg_type = 'can'
                ElmObd.send_response(msg=elm_response, msg_type='can')
            else:
                # elm_response.msg_type = 'at'
                # response_queue.put(elm_response)
                ElmObd.send_response(msg=elm_response, msg_type='at')


def run_dbus(ElmDbus):
    while(True):
        if (response_queue.empty() == False):
            #publish response
            response = response_queue.get()
            if response.msg_type == 'at':
                ElmDbus.emit_at_response(response.msg)
            elif response.msg_type == 'can':
                if ElmDbus.bEmitInterpCan is True:
                    # send msg to interp que
                    ElmDbus.watcher.CAN_handler(response.msg)
                if ElmDbus.bEmitRawCan is True:
                    ElmDbus.emit_at_response(response.msg)
            # response_queue.task_done()

# main loop run dbus object for elm
if __name__ == '__main__':

    dbus_loop = DBusGMainLoop(set_as_default=True)
    while dbus.SessionBus(mainloop=dbus_loop) is None:
        time.sleep(0.5)

    bus = dbus.SessionBus(mainloop=dbus_loop)

    # create dbus object
    elm_obd = ElmObd()
    # start thread on func

    # blocking setup call to start elm chip for the first time
    start_try_count = 0
    while(elm_obd.start_elm(SERIAL_DEVICE, BAUD_RATE) != 0):
        print 'could not start elm'
        start_try_count += 1
        if(start_try_count >= 5):
            exit()


    elm_dbus = ElmDbus(bus)

    elm_dbus.obd = elm_obd
    # we assume elm has started and we can talk to it...

    elm_obd.command_buffer_dump()

    elm_thread = Process(target=run_elm_obd, args=(elm_obd,))
    elm_dbus_thread = Process(target=run_dbus, args=(elm_dbus,))

    elm_thread.start()
    elm_dbus_thread.start()

    if CAN_AUTO_START == True:
        elm_dbus.monitor_can(silent=CAN_SILENT_MONITORING, format_can=False, header=True, spaces=True)

    dbus_loop.run()
