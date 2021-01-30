import tkinter as tk
from tkinter import ttk, filedialog, N, W, E, S
from utils import format_value
import logging
import threading

logger = logging.getLogger("MoonPrintGUI")


class PrintFile(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master, padding="10 10 10 10")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        self.master = master

        self._file = tk.StringVar()
        self._temp = tk.IntVar()
        self._thread = None

        self._create_widgets()

    def _quit(self):
        if self._thread is not None:
            self._thread.exit()

    def on_connect(self):
        self._print_btn.config(state=tk.NORMAL)

    def on_disconnect(self):
        self._print_btn.config(state=tk.DISABLED)

    def _create_widgets(self):
        ttk.Label(self, text="File").grid(column=0, row=0, sticky="nwes")
        ttk.Entry(self, textvariable=self._file).grid(column=1, row=0, sticky="nwes")
        ttk.Button(
            self, text="Select file", command=self._select_file
        ).grid(column=2, row=0, sticky=(N, W, E, S), padx=5)

        self._print_btn = ttk.Button(self, text="Print", command=self.start)
        self._print_btn.grid(column=0, row=1, sticky=(N, W, E, S), pady=20)
        self._print_btn.config(state=tk.DISABLED)

        self._progress = ttk.Progressbar(
            self, orient=tk.HORIZONTAL, length=300, mode='determinate'
        )
        self._progress.grid(column=0, row=2, sticky=(W, E), columnspan=3, pady=20)

        ttk.Label(self, text="Temperature:").grid(column=0, row=3, sticky="nwes")
        ttk.Label(self, textvariable=self._temp).grid(column=1, row=3, sticky="nwes")

    def _select_file(self):
        self._file.set(filedialog.askopenfilename())

    def get_lines(self, file):
        file_lines = file.readlines()
        self._progress.config(maximum=len(file_lines))

        values = {"X": "0000000", "Y": "0000000", "Z": "0000000", "E": "0000000"}

        for i, line in enumerate(file_lines):
            self._progress.config(value=i)

            if ";" in line:
                line = line[:line.index(";")]

            if line.startswith("G1 "):
                values.update({v[0]: format_value(v[1:]) for v in line[3:].split()})

                if "F" in values:
                    del values["F"]

                items = sorted(values.items())

                if "E" in values:
                    items.append(items.pop(0))

                line = "G1".ljust(5, " ") + " ".join(["".join(item) for item in items])

            elif line.startswith("M104") or line.startswith("M109"):
                pass

            elif line.startswith("G92"):
                _, value = line.split()
                line = "G92".ljust(5, " ") + f"{value[0]}{format_value(value[1:])}"

            else:
                continue

            yield line + "\n"

    def start(self):
        self._thread = threading.Thread(target=self.run)
        self._thread.start()

    def run(self):
        self._print_btn.config(state=tk.DISABLED)
        self.master.on_printing_start()

        s = self.master.connection.serial

        logger.info("start printing")

        with open(self._file.get(), "r") as f:
            for formatted_line in self.get_lines(f):
                while True:
                    logger.debug("waiting for OK . . .")
                    msg = s.readline().strip()

                    if msg == b"OK":
                        logger.debug("sending line")
                        logger.debug(formatted_line)
                        s.write(formatted_line.encode())
                        break
                    elif msg.startswith(b"T"):
                        temp = int(msg[1:].strip().decode())
                        self._temp.set(temp)
                    else:
                        logger.warning("got unexpected message: " + msg.decode() + "\n")

                logger.debug("formatting next line . . . ")

        self.master.on_printing_stop()
        logger.info("printing finished")
