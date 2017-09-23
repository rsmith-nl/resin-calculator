#!/usr/bin/env python3
# file: resin-calculator.py
# vim:fileencoding=utf-8:fdm=marker:ft=python
#
# Author: R.F. Smith <rsmith@xs4all.nl>
# Created: 2017-04-28 15:04:26 +0200
# Last modified: 2017-09-23 23:15:42 +0200
#
# To the extent possible under law, R.F. Smith has waived all copyright and
# related or neighboring rights to resin.py. This work is published
# from the Netherlands. See http://creativecommons.org/publicdomain/zero/1.0/
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

__version__ = '0.16.0'


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
    with open(os.environ['HOME'] + os.sep + 'resins.json') as rf:
        lines = rf.readlines()
    text = '\n'.join([ln.strip() for ln in lines])
    try:
        lm = re.search('// Last modified: (.*)', text).groups()[0]
    except AttributeError:
        lm = None
    nocomments = re.sub('^//.*$', '', text, flags=re.MULTILINE)
    return loads(nocomments), lm


class ResinCalcUI(tk.Tk):
    """GUI for the resin calculator."""

    def __init__(self, parent):
        """Create the UI object."""
        tk.Tk.__init__(self, parent)
        self.parent = parent
        self.current_recipe = None
        self.current_name = None
        self.quantity = 0
        self.initialize()

    def initialize(self):
        """Read the data file and create the GUI."""
        self.recepies, filedate = load_data()
        keys = sorted(list(self.recepies.keys()))
        # Set the font.
        default_font = nametofont("TkDefaultFont")
        default_font.configure(size=12)
        self.option_add("*Font", default_font)
        # General commands and bindings
        self.bind_all('q', self.do_exit)
        # Make selected rows and columns resizable
        self.columnconfigure(2, weight=1)
        self.rowconfigure(2, weight=1)
        # Create widgets.
        ttk.Label(
            self, text="Resin recipe:", anchor='e').grid(
                row=0, column=0, columnspan=2, sticky='we')
        resinchoice = ttk.Combobox(
            self, values=keys, state='readonly', justify='right', width=26)
        resinchoice.grid(row=0, column=2, columnspan=2, sticky='ew')
        resinchoice.bind("<<ComboboxSelected>>", self.on_resintype)
        self.resinchoice = resinchoice
        qt = ('Total quantity:', 'First component quantity:')
        quantitytype = ttk.Combobox(
            self, values=qt, state='readonly', justify='right', width=22)
        quantitytype.current(0)
        quantitytype.grid(row=1, column=0, columnspan=2, sticky='w')
        quantitytype.bind("<<ComboboxSelected>>", self.on_quantitytype)
        self.quantitytype = quantitytype
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
        result.column('ape', anchor='e', stretch=False, width=80)
        result.grid(row=2, column=0, columnspan=4, sticky='nesw')
        result.bind('<<UpdateNeeded>>', self.do_update)
        self.result = result
        prbut = ttk.Button(self, text="Print recipe", command=self.do_print)
        prbut.grid(row=3, column=0, sticky='w')
        savebut = ttk.Button(self, text="Save recipe", command=self.do_saveas)
        savebut.grid(row=3, column=1, sticky='w')
        if filedate:
            dflabel = ttk.Label(
                self, text='Data file modification date: ' + filedate,
                anchor='center', foreground='#777777'
            )
            dflabel.grid(row=4, column=1, columnspan=4, sticky='ew')
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
        val = self.quantitytype.current()
        if val != self.quantity:
            self.quantity = val
            self.result.event_generate('<<UpdateNeeded>>', when='tail')

    def get_amount(self):
        """Return the values of the amount entry field as a float."""
        value = self.qedit.get()
        if not value:
            quantity = 0
        else:
            quantity = float(value)
        return quantity

    def do_update(self, event):
        """
        Update callback.

        This callback is coupled to the synthetic <<UpdateNeeded>> event
        for the result widget. It updates the contents of that widget based
        on the contents of the entry and combobox widgets.
        """
        resin = self.resinchoice.get()
        if not resin:
            return
        quantity = self.get_amount()
        self.current_name = resin
        components = self.recepies[resin]
        if self.quantity == 0:
            factor = quantity / sum(c for _, c in components)
        else:
            factor = quantity / components[0][1]
        for item in self.result.get_children():
            self.result.delete(item)
        if quantity > 0:
            self.current_recipe = tuple((name, pround(c * factor),
                                         '{:.2f}'.format(
                                             int(100000 / (c * factor)) / 100))
                                        for name, c in components)
        else:
            self.current_recipe = tuple((name, 0, 0) for name, c in components)
        for name, amount, ape in self.current_recipe:
            self.result.insert("", 'end', values=(name, amount, 'g', ape))

    def make_text(self):
        """Create text representation of recipe."""
        s = '{:{}s}: {:>{}} {} ({:>{}} /kg)'
        q = self.get_amount()
        namelen = max(len(nm) for nm, amnt, _ in self.current_recipe)
        amlen = max(len(amnt) for _, amnt, _ in self.current_recipe)
        amlen = max((amlen, len(pround(q))))
        apulen = max(len(apu) for _, _, apu in self.current_recipe)
        lines = [
            'Resin calculator v' + __version__, '------------------------', '',
            'Recipe for: ' + self.current_name,
            'Date: ' + str(datetime.now())[:-7], 'User: ' + uname, ''
        ]
        lines += [
            s.format(name, namelen, amount, amlen, 'g', apu, apulen)
            for name, amount, apu in self.current_recipe
        ]
        lines += [
            '-'*(namelen + 4 + amlen),
            '{:{}s}{:>{}} {}'.format('', namelen+2, pround(q), amlen, 'g')]
        return '\n'.join(lines)

    def do_print(self):
        """Send recipe to a file, and print it."""
        if self.current_recipe is None:
            return
        text = self.make_text()
        filename = 'resin-calculator-output.txt'
        with open(filename, 'w') as pf:
            pf.write(text)
        printfile(filename)

    def do_saveas(self):
        """Save recipe to a file."""
        if self.current_recipe is None:
            return
        fn = filedialog.asksaveasfilename(
            parent=self, defaultextension='.txt',
            initialfile=self.current_name,
            initialdir=os.environ['HOME'])
        if not len(fn):
            return
        text = self.make_text()
        with open(fn, 'w') as pf:
            pf.write(text)


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

    # Detach from terminal.
    if os.fork():
        sys_exit()


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
