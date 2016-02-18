# test starting at low communication rate and changing to a higher communication rate

# import elm327
# from elm327.connection import *
# from elm327.obd import *

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

print("This will attempt to init the serial port at 9600 and then at 115200\n")

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

    serial1 = SerialConnectionFactory(port_class=Serial, baudrate=9600,
                                      parity=PARITY_NONE,
                                      timeout=0.5,
                                      write_timeout=0.1)

    connection1 = serial1.connect(SERIAL_DEVICE)

    obd1 = OBDInterface(connection1)

    print(obd1._send_command('ati'))

    # print(obd1._send_command('stbrt1000'))

    print(obd1._send_command('stsbr115200'))

    print("closing and reconnecting...")

    obd1._connection.close()

    try:
        serial2 = SerialConnectionFactory(port_class=Serial, baudrate=115200,
                                          parity=PARITY_NONE,
                                          timeout=0.5,
                                          write_timeout=0.1)
    except ValueError:
        print("value error")
        raise
    except SerialException:
        print("serial exception")
        raise

    connection2 = serial2.connect(SERIAL_DEVICE)

    obd2 = OBDInterface(connection2)

    print("trying for response")
    print(obd2._send_command("\r"))
    print(obd2._send_command("STI"))
