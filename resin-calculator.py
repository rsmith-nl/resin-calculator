#!/usr/bin/env python3
# file: resin-calculator.py
# vim:fileencoding=utf-8:fdm=marker:ft=python
#
# Copyright © 2017-2018 R.F. Smith <rsmith@xs4all.nl>.
# SPDX-License-Identifier: MIT
# Created: 2017-04-28T15:04:26+0200
# Last modified: 2019-08-20T11:12:49+0200
"""GUI for calculating resin amounts."""

from datetime import datetime
from json import loads
from sys import exit as sys_exit
import os
import re
import tkinter as tk
from tkinter import ttk
from tkinter.font import nametofont
from tkinter import messagebox
from tkinter import filedialog

__version__ = '1.4'


def pround(val):
    """Round a number with a precision determined by the magnitude."""
    precision = 1
    if val >= 100:
        precision = 0
    if val < 1:
        precision = 3
    return '{:.{}f}'.format(val, precision)


def load_data():
    """Load the resin data."""
    try:
        with open(os.environ['HOME'] + os.sep + 'resins.json') as rf:
            lines = rf.readlines()
    except FileNotFoundError:
        with open('resins.json') as rf:
            lines = rf.readlines()
    text = '\n'.join([ln.strip() for ln in lines])
    try:
        lm = re.search('// Last modified: (.*)', text).groups()[0]
    except AttributeError:
        lm = None
    nocomments = re.sub('^//.*$', '', text, flags=re.MULTILINE)
    return loads(nocomments), lm


def create_widgets(root):
    keys = sorted(list(recepies.keys()))
    default_font = nametofont("TkDefaultFont")
    default_font.configure(size=12)
    root.option_add("*Font", default_font)
    # General commands and bindings
    root.bind_all('q', do_exit)
    # Make selected rows and columns resizable
    root.columnconfigure(2, weight=1)
    root.rowconfigure(2, weight=1)
    # Create widgets.
    ttk.Label(
        root, text="Resin recipe:", anchor='e'
    ).grid(
        row=0, column=0, columnspan=2, sticky='we'
    )
    resinchoice = ttk.Combobox(root, values=keys, state='readonly', justify='right', width=26)
    resinchoice.grid(row=0, column=2, columnspan=2, sticky='ew')
    resinchoice.bind("<<ComboboxSelected>>", on_resintype)
    qt = ('Total quantity:', 'First component quantity:')
    quantitytype = ttk.Combobox(root, values=qt, state='readonly', justify='right', width=22)
    quantitytype.current(0)
    quantitytype.grid(row=1, column=0, columnspan=2, sticky='w')
    quantitytype.bind("<<ComboboxSelected>>", on_quantitytype)
    qedit = ttk.Entry(root, justify='right')
    qedit.insert(0, '100')
    qedit.grid(row=1, column=2, sticky='ew')
    vcmd = root.register(is_number)
    qedit['validate'] = 'key'
    qedit['validatecommand'] = (vcmd, '%P')
    ttk.Label(root, text='g').grid(row=1, column=3, sticky='w')
    result = ttk.Treeview(
        root, columns=('component', 'quantity', 'unit', 'ape'), selectmode="none",
    )
    style = ttk.Style(root)
    style.configure('Treeview', rowheight=24)
    result.heading('component', text='Component', anchor='w')
    result.heading('quantity', text='Quantity', anchor='e')
    result.heading('unit', text='Unit', anchor='w')
    result.heading('ape', text='1/kg', anchor='e')
    result.column('#0', width='0', stretch=False)
    result.column('component', anchor='w')
    result.column('quantity', anchor='e', stretch=False, width=100)
    result.column('unit', anchor='w', stretch=False, width=40)
    result.column('ape', anchor='e', stretch=False, width=80)
    result.grid(row=2, column=0, columnspan=4, sticky='nesw')
    result.bind('<<UpdateNeeded>>', do_update)
    prbut = ttk.Button(root, text="Print recipe", command=do_print)
    prbut.grid(row=3, column=0, sticky='w')
    savebut = ttk.Button(root, text="Save recipe", command=do_saveas)
    savebut.grid(row=3, column=1, sticky='w')
    if filedate:
        dflabel = ttk.Label(
            root,
            text='Data file modification date: ' + filedate,
            anchor='center',
            foreground='#777777'
        )
        dflabel.grid(row=4, column=1, columnspan=4, sticky='ew')
    resinchoice.focus_set()
    # Return the widgets that are referenced by other functions.
    return resinchoice, quantitytype, qedit, result


def is_number(data):
    """Validate the contents of an entry widget as a float."""
    if data == '':
        result.event_generate('<<UpdateNeeded>>', when='tail')
        return True
    try:
        rv = float(data)
        if rv < 0:
            return False
    except ValueError:
        return False
    result.event_generate('<<UpdateNeeded>>', when='tail')
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
    val = resinchoice.get()
    text2 = qedit.get()
    if val and text2:
        result.event_generate('<<UpdateNeeded>>', when='tail')
    qedit.focus_set()


def on_quantitytype(event):
    """Send update request when the quantity type has changed."""
    global qtype
    val = quantitytype.current()
    if val != qtype:
        qtype = val
        result.event_generate('<<UpdateNeeded>>', when='tail')


def get_amount():
    """Return the values of the amount entry field as a float."""
    value = qedit.get()
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
    global current_name, current_recipe
    resin = resinchoice.get()
    if not resin:
        return
    quant = get_amount()
    current_name = resin
    components = recepies[resin]
    if qtype == 0:
        factor = quant / sum(c for _, c in components)
    else:
        factor = quant / components[0][1]
    for item in result.get_children():
        result.delete(item)
    if quant > 0:
        current_recipe = tuple(
            (name, pround(c * factor), '{:.2f}'.format(int(100000 / (c * factor)) / 100))
            for name, c in components
        )
    else:
        current_recipe = tuple((name, 0, 0) for name, c in components)
    for name, amount, ape in current_recipe:
        result.insert("", 'end', values=(name, amount, 'g', ape))
    q = sum(float(amnt) for _, amnt, _ in current_recipe)
    result.insert("", 'end', values=('total:', pround(q), 'g', ''))


def make_text(recipe, name):
    """
    Create text representation of the current recipe.
    """
    s = '{:{}s}: {:>{}} {} ({:>{}} /kg)'
    q = sum(float(amnt) for _, amnt, _ in recipe)
    namelen = max(len(nm) for nm, amnt, _ in recipe)
    amlen = max(len(amnt) for _, amnt, _ in recipe)
    amlen = max((amlen, len(pround(q))))
    apulen = max(len(apu) for _, _, apu in recipe)
    lines = [
        'Resin calculator v' + __version__, '------------------------', '',
        'Recipe for: ' + name, 'Date: ' + str(datetime.now())[:-7],
        'User: ' + uname, ''
    ]
    lines += [
        s.format(name, namelen, amount, amlen, 'g', apu, apulen)
        for name, amount, apu in current_recipe
    ]
    lines += [
        '-' * (namelen + 4 + amlen),
        '{:{}s}{:>{}} {}'.format('', namelen + 2, pround(q), amlen, 'g')
    ]
    return '\n'.join(lines)


def do_print():
    """Send recipe to a file, and print it."""
    if current_recipe is None:
        return
    text = make_text(current_recipe, current_name)
    filename = 'resin-calculator-output.txt'
    with open(filename, 'w') as pf:
        pf.write(text)
    printfile(filename)


def do_saveas():
    """Save recipe to a file."""
    if current_recipe is None:
        return
    fn = filedialog.asksaveasfilename(
        parent=root,
        defaultextension='.txt',
        filetypes=(('text files', '*.txt'), ('all files', '*.*')),
        initialfile=current_name,
        initialdir=os.environ['HOME']
    )
    if not len(fn):
        return
    text = make_text(current_recipe, current_name)
    with open(fn, 'w') as pf:
        pf.write(text)


if __name__ == '__main__':
    # Platform specific set-up
    if os.name == 'nt':
        from win32api import ShellExecute
        from win32print import GetDefaultPrinter
        uname = os.environ['USERNAME']

        def printfile(fn):
            """Print the given file using the default printer."""
            dp = GetDefaultPrinter()
            rv = ShellExecute(0, 'print', fn, '/d: "{}"'.format(dp), '.', 0)
            if 0 < rv <= 32:
                messagebox.showerror('Printing failed', 'Error code: {}'.format(rv))

    elif os.name == 'posix':
        from subprocess import run
        uname = os.environ['USER']

        def printfile(fn):
            """Print the given file using “lpr”."""
            cp = run(['lpr', fn])
            if cp.returncode != 0:
                messagebox.showerror('Printing failed', 'Error code: {}'.format(cp.returncode))

        # Detach from terminal.
        if os.fork():
            sys_exit()

    else:
        uname = 'unknown'

        def printfile(fn):
            """Report that printing is not supported."""
            messagebox.showinfo('Printing', 'Printing is not supported on this OS.')

    # Global data
    recepies, filedate = load_data()
    qtype = 0
    quantity = 0
    current_recipe = None
    current_name = ''
    # Create and run the GUI.
    root = tk.Tk(None)
    resinchoice, quantitytype, qedit, result = create_widgets(root)
    root.wm_title('Resin calculator v' + __version__)
    root.mainloop()
