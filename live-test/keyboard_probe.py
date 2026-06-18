# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk


def main():
    output_path = sys.argv[1] if len(sys.argv) > 1 else "keyboard_probe_capture.txt"
    output_path = os.path.abspath(output_path)

    root = tk.Tk()
    root.title("Kiosk Keyboard Probe")
    root.geometry("520x160")
    root.attributes("-topmost", True)

    entry = tk.Entry(root, font=("Consolas", 18))
    entry.pack(fill="x", padx=24, pady=40)

    def write_capture(event=None):
        directory = os.path.dirname(output_path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with open(output_path, "w", encoding="utf-8") as capture_file:
            capture_file.write(entry.get())

    entry.bind("<KeyRelease>", write_capture)
    entry.focus_set()
    root.after(100, entry.focus_force)
    root.mainloop()


if __name__ == "__main__":
    main()
