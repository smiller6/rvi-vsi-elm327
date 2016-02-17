# test starting at low communication rate and changing to a higher communication rate

# import elm327
# from elm327.connection import *
# from elm327.obd import *

import time

from connection import *
from obd import *

# for getting vars from cli
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--serial_device", help="Serial device to connect")
# parser.add_argument("-b", "--baud_rate", help="Baud rate for communication",
#                     type=int)
args = parser.parse_args()

print("This will attempt to init the serial port at 9600 and then at 115200\n")

SERIAL_DEVICE = args.serial_device
# BAUD_RATE = args.baud_rate

trynewrate = True

if SERIAL_DEVICE:
    serial = SerialConnectionFactory(port_class=Serial, baudrate=9600)

    connection = serial.connect(SERIAL_DEVICE)

    obd = OBDInterface(connection)

    print(connection._port.name)
    print(connection._port.port)
    print(connection._port.baudrate)

    print((obd._send_command("ATI")))

    obd._connection._write("STBTR5000")
    # obd._send_command("STBTR5000")

    # obd._connection._write("STBR115200")
    obd._send_command("STBR115200")

    obd._connection.close()

    time.sleep(0.25)

    serial2 = SerialConnectionFactory(port_class=Serial, baudrate=115200)

    connection2 = serial2.connect(SERIAL_DEVICE)

    obd2 = OBDInterface(connection2)
    # print(obd._send_command("\n"))
    obd2._connection._port.write("\r")

    print(obd2._send_command("STI"))
    print(obd2._send_command("ATPPS"))
