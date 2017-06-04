#!/usr/bin/env python3
# file: resin-calculator.py
# vim:fileencoding=utf-8:fdm=marker:ft=python
#
# Author: R.F. Smith <rsmith@xs4all.nl>
# Created: 2017-04-28 15:04:26 +0200
# Last modified: 2017-06-04 15:48:36 +0200
#
# To the extent possible under law, R.F. Smith has waived all copyright and
# related or neighboring rights to resin.py. This work is published
# from the Netherlands. See http://creativecommons.org/publicdomain/zero/1.0/
"""GUI for calculating resin amounts."""

import json
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime

__version__ = '0.7'

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
            messagebox.showerror('Printing failed',
                                 'Error code: {}'.format(rv))

elif os.name == 'posix':
    from subprocess import run
    uname = os.environ['USER']

    def printfile(fn):
        """Print the given file using “lpr”."""
        cp = run(['lpr', fn])
        if cp.returncode != 0:
            messagebox.showerror('Printing failed',
                                 'Error code: {}'.format(cp.returncode))

else:
    uname = 'unknown'

    def printfile(fn):
        """Report that printing is not supported."""
        messagebox.showinfo('Printing',
                            'Printing is not supported on this OS.')
        pass


# Read the data-file
with open(os.environ['HOME'] + os.sep + 'resins.json') as rf:
    recepies = json.load(rf)
    keys = sorted(list(recepies.keys()))

# The currently selected recipe.
current_recipe = None
current_name = None

# Create and lay out the widgets
root = tk.Tk()
root.wm_title('Resin calculator v' + __version__)
ttk.Label(root, text="Resin:").grid(row=0, column=0, sticky='w')
choose = ttk.Combobox(root, values=keys, state='readonly')
choose.grid(row=0, column=1, columnspan=2, sticky='ew')
ttk.Label(root, text="Quantity:").grid(row=1, column=0, sticky='w')
qedit = ttk.Entry(root, justify='right')
qedit.insert(0, '100')
qedit.grid(row=1, column=1, sticky='ew')
ttk.Label(root, text='g').grid(row=1, column=2, sticky='w')
result = ttk.Treeview(root, columns=('component', 'quantity', 'unit', 'ape'))
result.heading('component', text='Component', anchor='w')
result.heading('quantity', text='Quantity', anchor='e')
result.heading('unit', text='Unit', anchor='w')
result.heading('ape', text='1/kg', anchor='e')
result.column('#0', width='0', stretch=False)
result.column('component', anchor='w')
result.column('quantity', anchor='e', stretch=False, width=100)
result.column('unit', anchor='w', stretch=False, width=40)
result.column('ape', anchor='e', stretch=False, width=60)
result.grid(row=2, column=0, columnspan=3, sticky='ew')
ttk.Button(root, text="Exit", command=root.quit).grid(row=3, column=2)
prbut = ttk.Button(root, text="Print")
prbut.grid(row=3, column=0)


def pround(val):
    """Round a number with a precision determined by the magnitude."""
    precision = 1
    if val >= 100:
        precision = 0
    if val < 1:
        precision = 3
    return '{:.{}f}'.format(val, precision)


# Callbacks
def on_combo(event):
    """Send update request when resin choice has changed."""
    global current_name
    val = choose.get()
    current_name = val
    text2 = qedit.get()
    if val and text2:
        result.event_generate('<<UpdateNeeded>>', when='tail')


def is_number(data):
    """Validate the contents of an entry widget as a float."""
    if data == '':
        return True
    try:
        rv = float(data)
        if rv == 0:
            return False
    except ValueError:
        return False
    result.event_generate('<<UpdateNeeded>>', when='tail')
    return True


def do_update(event):
    """
    Update callback.

    This callback is coupled to the synthetic <<UpdateNeeded>> event
    for the result widget. It updates the contents of that widget based on the
    contents of the entry and combobox widgets.
    """
    global current_recipe
    w = event.widget
    resin = choose.get()
    quantity = float(qedit.get())
    if not resin:
        return
    components = recepies[resin]
    factor = quantity / sum(c for _, c in components)
    current_recipe = tuple((name, pround(c * factor), '{:.2f}'.format(
        int(100000 / (c * factor)) / 100)) for name, c in components)
    for item in w.get_children():
        w.delete(item)
    for name, amount, ape in current_recipe:
        w.insert("", 'end', values=(name, amount, 'g', ape))


def do_print():
    """Send ouput to a file, and print it."""
    s = '{:{}s}: {:>{}} {}'
    namelen = max(len(nm) for nm, amnt in current_recipe)
    amlen = max(len(amnt) for nm, amnt in current_recipe)
    lines = [
        'Resin calculator v' + __version__, '---------------------', '',
        'Recipe for: ' + current_name, 'Date: ' + str(datetime.now())[:-7],
        'User: ' + uname, ''
    ]
    lines += [
        s.format(name, namelen, amount, amlen, 'g')
        for name, amount in current_recipe
    ]
    filename = 'resin-calculator-output.txt'
    with open(filename, 'w') as pf:
        pf.write('\n'.join(lines))
    printfile(filename)


# Connect the callbacks
vcmd = root.register(is_number)
qedit['validate'] = 'key'
qedit['validatecommand'] = (vcmd, '%P')
choose.bind("<<ComboboxSelected>>", on_combo)
result.bind('<<UpdateNeeded>>', do_update)
prbut['command'] = do_print

# Run the event loop.
root.mainloop()
