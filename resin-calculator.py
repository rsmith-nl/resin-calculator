#!/usr/bin/env python3
# file: resin-calculator.py
# vim:fileencoding=utf-8:fdm=marker:ft=python
#
# Author: R.F. Smith <rsmith@xs4all.nl>
# Created: 2017-04-28 15:04:26 +0200
# Last modified: 2017-08-06 19:49:49 +0200
#
# To the extent possible under law, R.F. Smith has waived all copyright and
# related or neighboring rights to resin.py. This work is published
# from the Netherlands. See http://creativecommons.org/publicdomain/zero/1.0/
"""GUI for calculating resin amounts."""

import json
import os
import tkinter as tk
from tkinter import ttk
from tkinter.font import nametofont
from tkinter import messagebox
from datetime import datetime

__version__ = '0.11'


def pround(val):
    """Round a number with a precision determined by the magnitude."""
    precision = 1
    if val >= 100:
        precision = 0
    if val < 1:
        precision = 3
    return '{:.{}f}'.format(val, precision)


class ResinCalcUI(tk.Tk):
    """GUI for the resin calculator."""

    def __init__(self, parent):
        """Create the UI object."""
        tk.Tk.__init__(self, parent)
        self.parent = parent
        self.current_recipe = None
        self.current_name = None
        self.quantity = 'Total'
        self.initialize()

    def initialize(self):
        """Read the data file and create the GUI."""
        with open(os.environ['HOME'] + os.sep + 'resins.json') as rf:
            self.recepies = json.load(rf)
            keys = sorted(list(self.recepies.keys()))
        # Set the font.
        default_font = nametofont("TkDefaultFont")
        default_font.configure(size=12)
        # General commands and bindings
        self.bind_all('q', self.do_exit)
        # Create widgets.
        ttk.Label(self, text="Resin recipe:").grid(
            row=0, column=0, columnspan=2, sticky='e')
        resinchoice = ttk.Combobox(self, values=keys, state='readonly')
        resinchoice.grid(row=0, column=2, columnspan=2, sticky='ew')
        resinchoice.bind("<<ComboboxSelected>>", self.on_resintype)
        self.resinchoice = resinchoice
        quantitytype = ttk.Combobox(
            self, values=('Total', 'First component'), state='readonly')
        quantitytype.current(0)
        quantitytype.grid(row=1, column=0, sticky='w')
        quantitytype.bind("<<ComboboxSelected>>", self.on_quantitytype)
        self.quantitytype = quantitytype
        ttk.Label(self, text=" quantity:").grid(row=1, column=1, sticky='w')
        qedit = ttk.Entry(self, justify='right')
        qedit.insert(0, '100')
        qedit.grid(row=1, column=2, sticky='ew')
        vcmd = self.register(self.is_number)
        qedit['validate'] = 'key'
        qedit['validatecommand'] = (vcmd, '%P')
        self.qedit = qedit
        ttk.Label(self, text='g').grid(row=1, column=3, sticky='w')
        result = ttk.Treeview(
            self,
            columns=('component', 'quantity', 'unit', 'ape'),
            selectmode="none")
        result.heading('component', text='Component', anchor='w')
        result.heading('quantity', text='Quantity', anchor='e')
        result.heading('unit', text='Unit', anchor='w')
        result.heading('ape', text='1/kg', anchor='e')
        result.column('#0', width='0', stretch=False)
        result.column('component', anchor='w')
        result.column('quantity', anchor='e', stretch=False, width=100)
        result.column('unit', anchor='w', stretch=False, width=40)
        result.column('ape', anchor='e', stretch=False, width=60)
        result.grid(row=2, column=0, columnspan=4, sticky='ew')
        result.bind('<<UpdateNeeded>>', self.do_update)
        self.result = result
        prbut = ttk.Button(self, text="Print", command=self.do_print)
        prbut.grid(row=3, column=0)
        self.resinchoice.focus_set()

    def is_number(self, data):
        """Validate the contents of an entry widget as a float."""
        if data == '':
            self.result.event_generate('<<UpdateNeeded>>', when='tail')
            return True
        try:
            rv = float(data)
            if rv < 0:
                return False
        except ValueError:
            return False
        self.result.event_generate('<<UpdateNeeded>>', when='tail')
        return True

    # Callbacks
    def do_exit(self, event):
        """
        Callback to handle quitting.

        This is necessary since the quit method does not take arguments.
        """
        self.quit()

    def on_resintype(self, event):
        """Send update request when resin choice has changed."""
        val = self.resinchoice.get()
        self.current_name = val
        text2 = self.qedit.get()
        if val and text2:
            self.result.event_generate('<<UpdateNeeded>>', when='tail')
        self.qedit.focus_set()

    def on_quantitytype(self, event):
        """Send update request when the quantity type has changed."""
        val = self.quantitytype.get()
        if val != self.quantity:
            self.quantity = val
            self.result.event_generate('<<UpdateNeeded>>', when='tail')

    def do_update(self, event):
        """
        Update callback.

        This callback is coupled to the synthetic <<UpdateNeeded>> event
        for the result widget. It updates the contents of that widget based
        on the contents of the entry and combobox widgets.
        """
        resin = self.resinchoice.get()
        value = self.qedit.get()
        if not value:
            quantity = 0
        else:
            quantity = float(value)
        if not resin:
            return
        self.current_name = resin
        components = self.recepies[resin]
        if self.quantity == 'Total':
            factor = quantity / sum(c for _, c in components)
        else:
            factor = quantity / components[0][1]
        for item in self.result.get_children():
            self.result.delete(item)
        if quantity > 0:
            self.current_recipe = tuple((name, pround(c * factor), '{:.2f}'.format(
                int(100000 / (c * factor)) / 100)) for name, c in components)
        else:
            self.current_recipe = tuple((name, 0, 0) for name, c in components)
        for name, amount, ape in self.current_recipe:
            self.result.insert("", 'end', values=(name, amount, 'g', ape))

    def do_print(self):
        """Send ouput to a file, and print it."""
        s = '{:{}s}: {:>{}} {}'
        namelen = max(len(nm) for nm, amnt, _ in self.current_recipe)
        amlen = max(len(amnt) for nm, amnt, _ in self.current_recipe)
        lines = [
            'Resin calculator v' + __version__, '---------------------', '',
            'Recipe for: ' + self.current_name,
            'Date: ' + str(datetime.now())[:-7], 'User: ' + uname, ''
        ]
        lines += [
            s.format(name, namelen, amount, amlen, 'g')
            for name, amount, _ in self.current_recipe
        ]
        filename = 'resin-calculator-output.txt'
        with open(filename, 'w') as pf:
            pf.write('\n'.join(lines))
        printfile(filename)


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


root = ResinCalcUI(None)
root.wm_title('Resin calculator v' + __version__)
root.mainloop()
