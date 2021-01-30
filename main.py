import tkinter as tk
from tkinter import ttk, messagebox, N, W, E, S
from serial import Serial, serialutil
from serial.tools import list_ports
import traceback
import logging
import sys
import os

from manual_controls import ManualControls
from print_file import PrintFile

logger = logging.getLogger("MoonPrintGUI")

if bool(os.getenv("DEBUG", False)):
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG)


class Connection(ttk.Frame):
    DEFAULT_BAUDRATE = 115200

    def __init__(self, master: "Application"):
        super().__init__(master, padding=(10, 10, 10, 20))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._serial = Serial()

        self.port = tk.StringVar(name="PORT")
        self.port.trace_add("write", self._update_values)

        self.baudrate = tk.IntVar(name="BAUDRATE")
        self.baudrate.trace_add("write", self._update_values)

        self.connected = tk.BooleanVar(value=False)

        self._create_widgets()
        self.baudrate.set(self.DEFAULT_BAUDRATE)

    @property
    def serial(self):
        return self._serial

    def _create_widgets(self):
        ttk.Label(self, text="Port").grid(column=0, row=0, sticky=W)
        self._port_input = ttk.Combobox(
            self, values=self.list_ports(), textvariable=self.port
        )
        self._port_input.grid(column=0, row=1, sticky=W)

        ttk.Label(self, text="Baudrate").grid(column=1, row=0, sticky=W)
        vcmd = (self.register(lambda x: x.isdecimal()), "%P")
        self._baudrate_input = ttk.Entry(
            self, textvariable=self.baudrate, validatecommand=vcmd, validate="all"
        )
        self._baudrate_input.grid(column=1, row=1, sticky=W)

        self._connect = ttk.Button(self, text="Connect", command=self.open)
        self._connect.grid(column=2, row=1, sticky=W)
        self._connect.config(state=tk.DISABLED)

    def _update_values(self, var, *_):
        if var == "PORT":
            self._serial.port = self.port.get()
        elif var == "BAUDRATE":
            self._serial.baudrate = self.baudrate.get()

        if self._serial.port and self._serial.baudrate:
            self._connect.config(state=tk.NORMAL)
        else:
            self._connect.config(state=tk.DISABLED)

    def open(self):
        try:
            self._serial.open()
        except serialutil.SerialException as e:
            traceback.print_exc()
            messagebox.showinfo(message=str(e))
            return

        logger.info(f"Connected to serial port {self._serial.port}")

        self._connect.config(text="Close", command=self.close)
        self._port_input.config(state=tk.DISABLED)
        self._baudrate_input.config(state=tk.DISABLED)
        self.master.on_connect()

    def close(self):
        self._serial.close()
        logger.info("Disconnected from serial port")

        self._connect.config(text="Connect", command=self.open)
        self._port_input.config(state=tk.NORMAL)
        self._baudrate_input.config(state=tk.NORMAL)
        self.master.on_disconnect()

    @staticmethod
    def list_ports():
        return [p.device for p in list_ports.comports()]


class Application(ttk.Frame):
    def __init__(self, master: tk.Tk = None):
        super().__init__(master, padding=(10, 10, 10, 10))
        self.grid(column=0, row=0, sticky=(N, W, E, S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        master.protocol("WM_DELETE_WINDOW", self._quit)

        self.master = master
        self.pack()

        self._create_widgets()

    @property
    def connection(self):
        return self._connection

    def on_connect(self):
        self._controls.on_connect()
        self._print.on_connect()

    def on_disconnect(self):
        self._controls.on_disconnect()
        self._print.on_disconnect()

    def on_printing_start(self):
        self._notebook.tab(0, state=tk.DISABLED)

    def on_printing_stop(self):
        self._notebook.tab(0, state=tk.NORMAL)

    def _quit(self):
        self._connection.close()
        self._controls.quit()
        self._print.quit()
        self.master.destroy()
        exit(0)

    def _create_widgets(self):
        self._connection = Connection(self)
        self._connection.grid(column=0, row=0, sticky=(N, W, E, S))

        self._notebook = ttk.Notebook(self)
        self._notebook.grid(column=0, row=2, sticky=(N, W, E, S))

        self._controls = ManualControls(self)
        self._controls.grid(column=0, row=3, sticky=(N, W, E, S))
        self._notebook.add(self._controls, text="Manual controls")

        self._print = PrintFile(self)
        self._print.grid(column=0, row=0, sticky=(N, W, E, S))
        self._notebook.add(self._print, text="Print file")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("MoonPrint GUI")
    app = Application(master=root)
    app.mainloop()
