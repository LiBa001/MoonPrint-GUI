from tkinter import ttk, N, W, E, S
import tkinter as tk
from enum import Enum
import threading
import logging
from utils import format_value

logger = logging.getLogger("MoonPrintGUI")


class Axes(ttk.Frame):
    def __init__(self, master: "ManualControls"):
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


class ExtruderState(Enum):
    REMOVE = -1
    IDLE = 0
    INSERT = 1


class Extruder(ttk.Frame):
    def __init__(self, master: "ManualControls"):
        super().__init__(master)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._extruder = tk.DoubleVar()
        self._multiplier = tk.IntVar(value=10)
        self._state = ExtruderState.IDLE

        self._create_widgets()

    def _create_widgets(self):
        ttk.Label(
            self, text="Extruder", font="Roboto 10 bold"
        ).grid(column=0, row=0, sticky=(W, E))

        ttk.Label(self, text="Multiplier").grid(column=0, row=1, sticky=(W, E))
        ttk.Spinbox(
            self, textvariable=self._multiplier, from_=1, to=1000, width=5
        ).grid(column=1, row=1, sticky=(W, E), padx=5)

        self._insert_btn = ttk.Button(
            self, text="Insert Filament", command=self._insert
        )
        self._insert_btn.grid(column=2, row=1, sticky=(W, E))

        self._remove_btn = ttk.Button(
            self, text="Remove Filament", command=self._remove
        )
        self._remove_btn.grid(column=3, row=1, sticky=(W, E))

        self._stop_btn = ttk.Button(self, text="Stop", command=self._stop)
        self._stop_btn.grid(column=4, row=1, sticky=(W, E))

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
        self._extruder.set(
            self._extruder.get() + self._state.value * self._multiplier.get()
        )


class Temperature(ttk.Frame):
    def __init__(self, master: "ManualControls"):
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
    def __init__(self, master: "ManualControls"):
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
            self.master.on_submitting_begin()
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
        self.master.on_submitting_begin()
        self._progress_bar.grid()
        self._progress_bar.start()

        self._submitting.set(True)

    def _on_submitted(self):
        self._progress_bar.stop()
        self._progress_bar.grid_remove()


class ManualControls(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._thread = None

        self._create_widgets()

    def _quit(self):
        if self._thread is not None:
            self._thread.exit()

    def _create_widgets(self):
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

    @property
    def connection(self):
        return self.master.connection

    def on_connect(self):
        self._submit.enable()

    def on_disconnect(self):
        self._submit.disable()

    def generate_gcode(self):
        while True:
            values = self._axes.coords
            values["e"] = self._extruder.extruder

            yield "G1".ljust(5, " ") + " ".join(
                ["".join((k.upper(), format_value(v))) for k, v in values.items()]
            ) + "\n"

            yield (
                "M104".ljust(5, " ") + "S"
                + format_value(self._temperature.target_temp, 3) + "\n"
            )

    def on_submitting_begin(self):
        if self._thread is None:
            self._start()

    def _start(self):
        logger.debug("starting thread")
        self._thread = threading.Thread(target=self.run)
        self._thread.start()

    def run(self):
        serial = self.connection.serial
        gcode_generator = self.generate_gcode()
        lines_submitted = 0

        while serial.is_open:
            msg = serial.readline().strip()
            if msg == b"OK":
                if self._submit.sync or self._submit.submitting:
                    self._extruder.run()

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
            elif msg.startswith(b"T"):
                temp = int(msg[1:].strip().decode())
                self._temperature.current_temp = temp
            else:
                logger.warning(f"Received unrecognized message: {msg.decode()}")
