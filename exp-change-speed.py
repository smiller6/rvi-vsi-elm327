# test starting at low communication rate and changing to a higher communication rate

# import elm327
# from elm327.connection import *
# from elm327.obd import *

import serial

from serial import *

from connection import *
from obd import *

# for getting vars from cli
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--serial_device", help="Serial device to connect")
# parser.add_argument("-b", "--baud_rate", help="Baud rate for communication",
#                     type=int)
args = parser.parse_args()

print("This will attempt to init the serial port at 9600 and then at 500000\n")

SERIAL_DEVICE = args.serial_device
# BAUD_RATE = args.baud_rate



if SERIAL_DEVICE:

    # serial = SerialConnectionFactory(port_class=Serial, baudrate=9600)

    ser = serial.Serial(SERIAL_DEVICE,
                        baudrate=9600,
                        parity=PARITY_NONE,
                        timeout=0.25,
                        write_timeout=0.1)

    ser.close()

    ser = SerialConnectionFactory(port_class=Serial, baudrate=9600,
                                  parity=PARITY_NONE,
                                  timeout=0.5,
                                  write_timeout=0.1)

    connection = ser.connect(SERIAL_DEVICE)

    obd = OBDInterface(connection)

    print(obd._send_command('ati'))

    # print(obd1._send_command('stbrt1000'))

    print(obd._send_command('stsbr500000'))

    print("closing and reconnecting...")

    obd._connection.close()

    try:
        ser = SerialConnectionFactory(port_class=Serial, baudrate=500000,
                                      parity=PARITY_NONE,
                                      timeout=0.5,
                                      write_timeout=0.1)
    except ValueError:
        print("value error")
        raise
    except SerialException:
        print("serial exception")
        raise

    connection = ser.connect(SERIAL_DEVICE)

    obd = OBDInterface(connection)

    print("trying for response")
    print(obd._send_command("\r"))
    print(obd._send_command("STI"))

    print(obd._send_command("ath1"))
    print(obd._send_command("atcaf0"))
    print(obd._send_command("atcsm0"))
    print(obd._send_command("atma"))
    # danger
    while (True):
        line = obd._connection._read()
        if line:
            print(line)
