import argparse
import dbus
import dbus.mainloop.glib
import dbus.service
import gtk

elm_name = "rvi.vsi.ElmDbus"
elm_path = "/rvi/vsi/ElmDbus/object"


parser = argparse.ArgumentParser(description=('Provoke the Elm Dbus object '+elm_name))

#parser.add_argument('-m', '--method', help='Method to invoke')
#parser.add_argument('-a', '--args', help='Method args', nargs='*')

parser.add_argument('-c', '--watch-can', help='Start an object that watches the CAN signals')
#parser.add_argument('-s', '--signal', help='Signal to watch')

args = parser.parse_args()

# method = args.method
# nargs = args.args

class ElmDbusCanWatcher(dbus.service.Object):

    def __init__(self, conn, object_path='/rvi/vsi/ElmDbusCanWatcher/object'):
        dbus.service.Object.__init__(self, conn, object_path)

    def CAN_signal_handler(self, can_message=None):
        print(can_message)


if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus = dbus.SessionBus()

    if args.watch_can:

        watcher = ElmDbusCanWatcher(bus)

        elm = bus.get_object(elm_name, elm_path)

        elm.connect_to_signal('can_response', watcher.CAN_signal_handler,
                              dbus_interface=elm_name)

        monitor_can = elm.get_dbus_method('monitor_can', dbus_interface=elm_name)

        silent = False
        format = True
        header = True
        spaces = True

        monitor_can(silent, format, header, spaces)

    gtk.main()
