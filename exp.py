# test of opening a port, query ELM chip

# import elm327
# from elm327.connection import *
# from elm327.obd import *

from connection import *
from obd import *

# for getting vars from cli
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--serial_device", help="Serial device to connect")
parser.add_argument("-b", "--baud_rate", help="Baud rate for communication",
                    type=int)
args = parser.parse_args()

SERIAL_DEVICE = args.serial_device
BAUD_RATE = args.baud_rate

if SERIAL_DEVICE:
    if BAUD_RATE >= 9600 and BAUD_RATE <= 115200:

        serial = SerialConnectionFactory(port_class=Serial, baudrate=BAUD_RATE)

        connection = serial.connect(SERIAL_DEVICE)

        obd = OBDInterface(connection)

        print((obd._send_command("ATZ")))
    else:
        print("Baud rate incorrect. Supply range 9600:115200")

else:
    print("Insufficient args provided.\n"
          "Please supply serial device and baudrate\n")
