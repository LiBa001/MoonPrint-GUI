import tkinter as tk
from tkinter import ttk, messagebox, N, W, E, S
from serial import Serial, serialutil
from serial.tools import list_ports
import traceback
import logging
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class ExtruderState(Enum):
    REMOVE = -1
    IDLE = 0
    INSERT = 1


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


class Axes(ttk.Frame):
    def __init__(self, master: "Application"):
        super().__init__(master)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._coords = {"x": tk.DoubleVar(), "y": tk.DoubleVar(), "z": tk.DoubleVar()}

        self._create_widgets()

    def _create_widgets(self):
        ttk.Label(
            self, text="Axes", font="Roboto 10 bold"
        ).grid(column=0, row=0, sticky=(W, E))

        for i, (coord_name, coord_var) in enumerate(self._coords.items()):
            ttk.Label(self, text=coord_name.upper()).grid(column=0, row=i+1, sticky=W)
            ttk.Spinbox(
                self, textvariable=coord_var, from_=0, to=1000
            ).grid(column=1, row=i+1, sticky=(W, E))
            ttk.Scale(
                self,
                orient=tk.HORIZONTAL,
                length=200,
                from_=0,
                to=1000,
                variable=coord_var
            ).grid(column=2, row=i+1, sticky=E)

    @property
    def coords(self):
        return {k: v.get() for k, v in self._coords.items()}

    @property
    def x(self):
        return self._coords["x"].get()

    @property
    def y(self):
        return self._coords["y"].get()

    @property
    def z(self):
        return self._coords["z"].get()


class Extruder(ttk.Frame):
    def __init__(self, master: "Application"):
        super().__init__(master)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._extruder = tk.DoubleVar()
        self._state = ExtruderState.IDLE

        self._create_widgets()

    def _create_widgets(self):
        ttk.Label(
            self, text="Extruder", font="Roboto 10 bold"
        ).grid(column=0, row=0, sticky=(W, E))

        self._insert_btn = ttk.Button(
            self, text="Insert Filament", command=self._insert
        )
        self._insert_btn.grid(column=0, row=1, sticky=(W, E))

        self._remove_btn = ttk.Button(
            self, text="Remove Filament", command=self._remove
        )
        self._remove_btn.grid(column=1, row=1, sticky=(W, E))

        self._stop_btn = ttk.Button(self, text="Stop", command=self._stop)
        self._stop_btn.grid(column=2, row=1, sticky=(W, E))

        self._enable()

    def _insert(self):
        self._state = ExtruderState.INSERT
        self._disable()

    def _remove(self):
        self._state = ExtruderState.REMOVE
        self._disable()

    def _stop(self):
        self._state = ExtruderState.IDLE
        self._enable()

    def _disable(self):
        self._insert_btn.config(state=tk.DISABLED)
        self._remove_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.NORMAL)

    def _enable(self):
        self._insert_btn.config(state=tk.NORMAL)
        self._remove_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.DISABLED)

    @property
    def extruder(self):
        return self._extruder.get()

    def run(self):
        self._extruder += self._state.value


class Temperature(ttk.Frame):
    def __init__(self, master: "Application"):
        super().__init__(master)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._current_temp = tk.IntVar()
        self._target_temp = tk.IntVar()

        self._create_widgets()

    def _create_widgets(self):
        ttk.Label(
            self, text="Hot End", font="Roboto 10 bold"
        ).grid(column=0, row=0, sticky=(W, E))

        ttk.Label(self, text="Current Temp.").grid(column=0, row=1, sticky=W, )
        ttk.Label(self, textvariable=self._current_temp).grid(column=1, row=1, sticky=W)

        ttk.Label(self, text="Target Temp.").grid(column=0, row=2, sticky=W)
        ttk.Spinbox(
            self, textvariable=self._target_temp, from_=0, to=300
        ).grid(column=1, row=2, sticky=(W, E))

    @property
    def current_temp(self):
        return self._current_temp.get()

    @current_temp.setter
    def current_temp(self, value: int):
        self._current_temp.set(value)

    @property
    def target_temp(self):
        return self._target_temp.get()


class Submit(ttk.Frame):
    def __init__(self, master: "Application"):
        super().__init__(master)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._submit: ttk.Button
        self._sync = tk.BooleanVar(value=False)
        self._submitting = tk.BooleanVar(value=False)
        self._submitting.trace_add("write", self._on_state_change)

        self._create_widgets()

    def _create_widgets(self):
        self._submit = ttk.Button(self, text="Submit", command=self._on_submit)
        self._submit.grid(column=0, row=0, sticky=(W, S))
        self._sync_checkbox = ttk.Checkbutton(
            self,
            text="Automatically sync with Printer",
            variable=self._sync,
            command=self._change_sync
        )
        self._sync_checkbox.grid(column=0, row=1, sticky=(W, S))

        self._progress_bar = ttk.Progressbar(
            self, orient=tk.HORIZONTAL, length=200, mode='indeterminate'
        )
        self._progress_bar.grid(column=1, row=0, sticky=E)
        self._progress_bar.grid_remove()

        self.disable()

    def _change_sync(self):
        if self._sync.get():
            self._submit.config(state=tk.DISABLED)
        else:
            self._submit.config(state=tk.NORMAL)

    def _on_state_change(self, *_):
        if not self.submitting:
            self._on_submitted()

    @property
    def sync(self):
        return self._sync.get()

    @property
    def submitting(self) -> bool:
        return self._submitting.get()

    @submitting.setter
    def submitting(self, value: bool):
        self._submitting.set(value)

    def disable(self):
        self._submit.config(state=tk.DISABLED)
        self._sync_checkbox.config(state=tk.DISABLED)

    def enable(self):
        self._submit.config(state=tk.NORMAL)
        self._sync_checkbox.config(state=tk.NORMAL)

    def _on_submit(self):
        self._progress_bar.grid()
        self._progress_bar.start()

        self._submitting.set(True)

    def _on_submitted(self):
        self._progress_bar.stop()
        self._progress_bar.grid_remove()


class Application(ttk.Frame):
    def __init__(self, master: tk.Tk = None):
        super().__init__(master, padding=(10, 10, 10, 10))
        self.grid(column=0, row=0, sticky=(N, W, E, S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master
        self.pack()

        self._create_widgets()

    def _create_widgets(self):
        self._connection = Connection(self)
        self._connection.grid(column=0, row=0, sticky=(N, W, E))
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(column=0, row=1, sticky=(W, E))

        self._axes = Axes(self)
        self._axes.grid(column=0, row=2, sticky=(N, W, E))

        self._extruder = Extruder(self)
        self._extruder.grid(column=0, row=3, sticky=(N, W, E))

        self._temperature = Temperature(self)
        self._temperature.grid(column=0, row=4, sticky=(N, W, E))

        ttk.Separator(self, orient=tk.HORIZONTAL).grid(column=0, row=5, sticky=(W, E))

        self._submit = Submit(self)
        self._submit.grid(column=0, row=6, sticky=(W, E, S))

        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)

    def on_connect(self):
        self._submit.enable()
        threading.Thread(target=self.run).start()

    def on_disconnect(self):
        self._submit.disable()

    def generate_gcode(self):
        while True:
            values = self._axes.coords
            values["e"] = self._extruder.extruder

            yield "G1".ljust(5, " ") + " ".join(
                ["".join((k.upper(), self.format_value(v))) for k, v in values.items()]
            ) + "\n"

            yield (
                "M104".ljust(5, " ") + "S"
                + self.format_value(self._temperature.target_temp) + "\n"
            )

    def run(self):
        serial = self._connection.serial
        gcode_generator = self.generate_gcode()
        lines_submitted = 0

        while serial.is_open:
            msg = serial.readline().strip()
            if msg == b"OK":
                gcode = next(gcode_generator)
                if self._submit.sync:
                    logger.debug(f"syncing with gcode: {gcode}")
                    serial.write(gcode.encode())
                elif self._submit.submitting:
                    logger.debug(f"submitting gcode: {gcode}")
                    serial.write(gcode.encode())
                    lines_submitted += 1

                    if lines_submitted >= 2:
                        self._submit.submitting = False
                        lines_submitted = 0
            else:
                logger.warning(f"Received unrecognized message: {msg.decode()}")

    @staticmethod
    def format_value(value):
        return str(value).rjust(7, "0")[:7]


if __name__ == "__main__":
    root = tk.Tk()
    root.title("MoonPrint GUI")
    app = Application(master=root)
    app.mainloop()
