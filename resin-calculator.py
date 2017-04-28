#!/usr/bin/env python3
# file: resin-calculator.py
# vim:fileencoding=utf-8:fdm=marker:ft=python
#
# Author: R.F. Smith <rsmith@xs4all.nl>
# Created: 2017-04-28 15:04:26 +0200
# Last modified: 2017-04-28 20:03:24 +0200
#
# To the extent possible under law, R.F. Smith has waived all copyright and
# related or neighboring rights to resin.py. This work is published
# from the Netherlands. See http://creativecommons.org/publicdomain/zero/1.0/

"""GUI for calculating resin amounts."""

import json
import os
import tkinter as tk
from tkinter import ttk

with open(os.environ['HOME']+os.sep+'recepten.json') as rf:
    recepies = json.load(rf)
    keys = sorted(list(recepies.keys()))

# The currently selected recipe.
current_recipe = ()

# Create and lay out the widgets
root = tk.Tk()
root.wm_title('Resin calculator')
ttk.Label(root, text="Resin:").grid(row=0, column=0, sticky='w')
choose = ttk.Combobox(root, values=keys, state='readonly')
choose.grid(row=0, column=1, columnspan=2, sticky='ew')
ttk.Label(root, text="Quantity:").grid(row=1, column=0, sticky='w')
qedit = ttk.Entry(root, justify='right')
qedit.insert(0, '100')
qedit.grid(row=1, column=1, sticky='ew')
units = ttk.Combobox(root, values=('g', 'kg', 'lb'), state='readonly')
units.current(0)
units.grid(row=1, column=2, sticky='w')
result = ttk.Treeview(root, columns=('component', 'quantity', 'unit'))
result.heading('component', text='Component', anchor='w')
result.heading('quantity', text='Quantity', anchor='e')
result.heading('unit', text='Unit', anchor='w')
result.column('#0', width='0', stretch=False)
result.column('component', anchor='w')
result.column('quantity', anchor='e', stretch=False, width=100)
result.column('unit', anchor='w', stretch=False, width=40)
result.grid(row=2, column=0, columnspan=3, sticky='ew')
exit = ttk.Button(root, text="Exit", command=root.quit).grid(row=3, column=2)


# Callbacks
def on_combo(event):
    val = choose.get()
    text2 = qedit.get()
    if val and text2:
        result.event_generate('<<UpdateNeeded>>', when='tail')


def is_number(data):
    if data == '':
        return True
    try:
        float(data)
    except ValueError:
        return False
    result.event_generate('<<UpdateNeeded>>', when='tail')
    return True


def do_update(event):
    w = event.widget
    resin = choose.get()
    u = units.get()
    quantity = float(qedit.get())
    if not resin:
        return
    components = recepies[resin]
    factor = quantity/sum(c for _, c in components)
    current_recipe = tuple((name, c*factor)
                           for name, c in components)
    for item in w.get_children():
        w.delete(item)
    for name, amount in current_recipe:
        precision = 1
        if amount >= 100:
            precision = 0
        elif amount < 1:
            precision = 3
        w.insert("", 'end', values=(name, '{:.{}f}'.format(amount, precision), u))


# Connect the callbacks
vcmd = root.register(is_number)
qedit['validate'] = 'key'
qedit['validatecommand'] = (vcmd, '%P')
choose.bind("<<ComboboxSelected>>", on_combo)
units.bind("<<ComboboxSelected>>", on_combo)
result.bind('<<UpdateNeeded>>', do_update)

# Run the event loop.
root.mainloop()
