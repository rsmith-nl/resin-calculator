#!/usr/bin/env python3
# file: resin-calculator.py
# vim:fileencoding=utf-8:fdm=marker:ft=python
#
# Copyright © 2017-2018 R.F. Smith <rsmith@xs4all.nl>.
# SPDX-License-Identifier: MIT
# Created: 2017-04-28T15:04:26+0200
# Last modified: 2020-12-02T23:26:28+0100
"""GUI for calculating resin amounts."""

from datetime import datetime
from json import loads
from sys import exit as sys_exit
from types import SimpleNamespace
import os
import re
import tkinter as tk
from tkinter import ttk
from tkinter.font import nametofont
from tkinter import messagebox
from tkinter import filedialog

__version__ = "2020.12.02"


def pround(val):
    """Round a number with a precision determined by the magnitude."""
    precision = 1
    if val >= 100:
        precision = 0
    if val < 1:
        precision = 3
    return f"{val:.{precision}f}"


def load_data():
    """Load the resin data."""
    try:
        with open(_home + os.sep + "resins.json") as rf:
            lines = rf.readlines()
    except (FileNotFoundError, KeyError):
        with open("resins.json") as rf:
            lines = rf.readlines()
    text = "\n".join([ln.strip() for ln in lines])
    try:
        lm = re.search("// Last modified: (.*)", text).groups()[0]
    except AttributeError:
        lm = None
    nocomments = re.sub("^//.*$", "", text, flags=re.MULTILINE)
    return loads(nocomments), lm


def create_widgets(root):
    keys = sorted(list(state.recepies.keys()))
    default_font = nametofont("TkDefaultFont")
    default_font.configure(size=12)
    root.option_add("*Font", default_font)
    # Make selected rows and columns resizable
    root.columnconfigure(2, weight=1)
    root.rowconfigure(2, weight=1)
    # Create widgets.
    ttk.Label(root, text="Resin recipe:", anchor="e").grid(
        row=0, column=0, columnspan=2, sticky="we"
    )
    resinchoice = ttk.Combobox(
        root, values=keys, state="readonly", justify="right", width=26
    )
    resinchoice.grid(row=0, column=2, columnspan=2, sticky="ew")
    resinchoice.bind("<<ComboboxSelected>>", on_resintype)
    qt = ("Total quantity:", "First component quantity:")
    quantitytype = ttk.Combobox(
        root, values=qt, state="readonly", justify="right", width=22
    )
    quantitytype.current(0)
    quantitytype.grid(row=1, column=0, columnspan=2, sticky="w")
    quantitytype.bind("<<ComboboxSelected>>", on_quantitytype)
    qedit = ttk.Entry(root, justify="right")
    qedit.insert(0, "100")
    qedit.grid(row=1, column=2, sticky="ew")
    vcmd = root.register(is_number)
    qedit["validate"] = "key"
    qedit["validatecommand"] = (vcmd, "%P")
    ttk.Label(root, text="g").grid(row=1, column=3, sticky="w")
    result = ttk.Treeview(
        root,
        columns=("component", "quantity", "unit", "ape"),
        selectmode="none",
    )
    style = ttk.Style(root)
    style.configure("Treeview", rowheight=24)
    result.heading("component", text="Component", anchor="w")
    result.heading("quantity", text="Quantity", anchor="e")
    result.heading("unit", text="Unit", anchor="w")
    result.heading("ape", text="1/kg", anchor="e")
    result.column("#0", width="0", stretch=False)
    result.column("component", anchor="w")
    result.column("quantity", anchor="e", stretch=False, width=100)
    result.column("unit", anchor="w", stretch=False, width=40)
    result.column("ape", anchor="e", stretch=False, width=80)
    result.grid(row=2, column=0, columnspan=4, sticky="nesw")
    result.bind("<<UpdateNeeded>>", do_update)
    prbut = ttk.Button(root, text="Print recipe", command=do_print)
    prbut.grid(row=3, column=0, sticky="w")
    savebut = ttk.Button(root, text="Save recipe", command=do_saveas)
    savebut.grid(row=3, column=1, sticky="w")
    if state.filedate:
        dflabel = ttk.Label(
            root,
            text="Data file modification date: " + state.filedate,
            anchor="center",
            foreground="#777777",
        )
        dflabel.grid(row=4, column=1, columnspan=4, sticky="ew")
    resinchoice.focus_set()
    # Return the widgets that are referenced by other functions.
    w = SimpleNamespace(
        resinchoice=resinchoice, quantitytype=quantitytype, qedit=qedit, result=result
    )
    return w


def is_number(data):
    """Validate the contents of an entry widget as a float."""
    if data == "":
        w.result.event_generate("<<UpdateNeeded>>", when="tail")
        return True
    try:
        rv = float(data)
        if rv < 0:
            return False
    except ValueError:
        return False
    w.result.event_generate("<<UpdateNeeded>>", when="tail")
    return True


# Callbacks
def do_exit(event):
    """
    Callback to handle quitting.
    """
    root.destroy()


def on_resintype(event):
    """
    Send update request when resin choice has changed, and both the resin choice
    and quantity are not empty.
    """
    val = w.resinchoice.get()
    text2 = w.qedit.get()
    if val and text2:
        w.result.event_generate("<<UpdateNeeded>>", when="tail")
    w.qedit.focus_set()


def on_quantitytype(event):
    """Send update request when the quantity type has changed."""
    # global qtype
    val = w.quantitytype.current()
    if val != state.qtype:
        state.qtype = val
        w.result.event_generate("<<UpdateNeeded>>", when="tail")


def get_amount():
    """Return the values of the amount entry field as a float."""
    value = w.qedit.get()
    if not value:
        quantity = 0
    else:
        quantity = float(value)
    return quantity


def do_update(event):
    """
    Update callback.

    This callback is coupled to the synthetic <<UpdateNeeded>> event
    for the result widget. It updates the contents of that widget based
    on the contents of the entry and combobox widgets.
    """
    # global current_name, current_recipe
    resin = w.resinchoice.get()
    if not resin:
        return
    quant = get_amount()
    state.current_name = resin
    components = state.recepies[resin]
    if state.qtype == 0:
        factor = quant / sum(c for _, c in components)
    else:
        factor = quant / components[0][1]
    for item in w.result.get_children():
        w.result.delete(item)
    if quant > 0:
        state.current_recipe = tuple(
            (name, pround(c * factor), f"{int(100000/(c*factor))/100:.2f}")
            for name, c in components
        )
    else:
        state.current_recipe = tuple((name, 0, 0) for name, c in components)
    for name, amount, ape in state.current_recipe:
        w.result.insert("", "end", values=(name, amount, "g", ape))
    q = sum(float(amnt) for _, amnt, _ in state.current_recipe)
    w.result.insert("", "end", values=("total:", pround(q), "g", ""))


def make_text(state):
    """
    Create text representation of the current recipe.
    """
    q = sum(float(amnt) for _, amnt, _ in state.current_recipe)
    namelen = max(len(nm) for nm, amnt, _ in state.current_recipe)
    amlen = max(len(amnt) for _, amnt, _ in state.current_recipe)
    amlen = max((amlen, len(pround(q))))
    apulen = max(len(apu) for _, _, apu in state.current_recipe)
    lines = [
        f"Resin calculator v{__version__}",
        "------------------------",
        "",
        f"Recipe for: {state.current_name}",
        f"Date: {str(datetime.now())[:-7]}",
        "User: {_uname}",
        "",
    ]
    lines += [
        f"{name:{namelen}s}: {amount:>{amlen}} g ({apu:>{apulen}} /kg)"
        for name, amount, apu in state.current_recipe
    ]
    lines += ["-" * (namelen + 4 + amlen), f'{"":{namelen + 2}s}{pround(q):>{amlen}} g']
    return "\n".join(lines)


def do_print(event):
    """Send recipe to a file, and print it."""
    if state.current_recipe is None:
        return
    text = make_text(state.current_recipe, state.current_name, state)
    filename = "resin-calculator-output.txt"
    with open(filename, "w") as pf:
        pf.write(text)
    _printfile(filename)


def do_saveas():
    """Save recipe to a file."""
    if state.current_recipe is None:
        return
    fn = filedialog.asksaveasfilename(
        parent=root,
        defaultextension=".txt",
        filetypes=(("text files", "*.txt"), ("all files", "*.*")),
        initialfile=state.current_name,
        initialdir=_home,
    )
    if not len(fn):
        return
    text = make_text(state)
    with open(fn, "w") as pf:
        pf.write(text)


if __name__ == "__main__":
    # Platform specific set-up
    if os.name == "nt":
        from win32api import ShellExecute
        from win32print import GetDefaultPrinter

        _uname = os.environ["USERNAME"]
        _home = os.environ["HOMEPATH"]

        def _printfile(fn):
            """Print the given file using the default printer."""
            dp = GetDefaultPrinter()
            rv = ShellExecute(0, "print", fn, f'/d: "{dp}"', ".", 0)
            if 0 < rv <= 32:
                messagebox.showerror("Printing failed", f"Error code: {rv}")

    elif os.name == "posix":
        from subprocess import run

        _uname = os.environ["USER"]
        _home = os.environ["HOME"]

        def _printfile(fn):
            """Print the given file using “lpr”."""
            cp = run(["lpr", fn])
            if cp.returncode != 0:
                messagebox.showerror("Printing failed", f"Error code: {cp.returncode}")

        # Detach from terminal.
        if os.fork():
            sys_exit()

    else:
        _uname = "unknown"
        _home = "unknown"

        def _printfile(fn):
            """Report that printing is not supported."""
            messagebox.showinfo("Printing", "Printing is not supported on this OS.")

    # Global data
    state = SimpleNamespace()
    state.recepies, state.filedate = load_data()
    state.qtype = 0
    state.quantity = 0
    state.current_recipe = None
    state.current_name = ""
    # Create and run the GUI.
    root = tk.Tk(None)
    w = create_widgets(root)
    root.wm_title("Resin calculator v" + __version__)
    root.mainloop()
