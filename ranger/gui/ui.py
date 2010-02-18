# Copyright (C) 2009, 2010  Roman Zimbelmann <romanz@lavabit.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socket
import sys
import curses
import _curses

from .displayable import DisplayableContainer
from ranger.container.keymap import CommandArgs
from .mouse_event import MouseEvent

class UI(DisplayableContainer):
	is_set_up = False
	mousemask = curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION
	load_mode = False
	def __init__(self, keymap=None, env=None, fm=None):
		import os
		os.environ['ESCDELAY'] = '25'   # don't know a cleaner way

		if env is not None:
			self.env = env
		if fm is not None:
			self.fm = fm

		if keymap is None:
			self.keymap = self.settings.keys.ui_keys
		else:
			self.keymap = keymap
		self.win = curses.initscr()
		self.env.keybuffer.assign(self.keymap, self.settings.keys.directions)
		self.env.keybuffer.clear()

		DisplayableContainer.__init__(self, None)

	def initialize(self):
		"""initialize curses, then call setup (at the first time) and resize."""
		self.win.leaveok(0)
		self.win.keypad(1)
		self.load_mode = False

		curses.cbreak()
		curses.noecho()
		curses.halfdelay(20)
		try:
			curses.curs_set(int(bool(self.settings.show_cursor)))
		except:
			pass
		curses.start_color()
		curses.use_default_colors()

		curses.mousemask(self.mousemask)
		curses.mouseinterval(0)

		## this line solves this problem:
		## If an action, following a mouse click, includes the
		## suspension and re-initializion of the ui (e.g. running a
		## file by clicking on its preview) and the next key is another
		## mouse click, the bstate of this mouse event will be invalid.
		## (atm, invalid bstates are recognized as scroll-down)
		curses.ungetmouse(0,0,0,0,0)

		if not self.is_set_up:
			self.is_set_up = True
			self.setup()
		self.update_size()

	def suspend(self):
		"""Turn off curses"""
		# from ranger import log
		# log("suspending ui!")
		self.win.keypad(0)
		curses.nocbreak()
		curses.echo()
		try:
			curses.curs_set(1)
		except:
			pass
		curses.mousemask(0)
		curses.endwin()

	def set_load_mode(self, boolean):
		boolean = bool(boolean)
		if boolean != self.load_mode:
			self.load_mode = boolean

			if boolean:
				# don't wait for key presses in the load mode
				curses.cbreak()
				self.win.nodelay(1)
			else:
				self.win.nodelay(0)
				curses.halfdelay(20)

	def destroy(self):
		"""Destroy all widgets and turn off curses"""
		DisplayableContainer.destroy(self)
		self.suspend()

	def handle_mouse(self):
		"""Handles mouse input"""
		try:
			event = MouseEvent(curses.getmouse())
		except _curses.error:
			return

		# from ranger import log
		# log('{0:0>28b} ({0})'.format(event.bstate))
		# log('y: {0}  x: {1}'.format(event.y, event.x))

		DisplayableContainer.click(self, event)

	def handle_key(self, key):
		"""Handles key input"""

		if hasattr(self, 'hint'):
			self.hint()

		self.env.key_append(key)

		if DisplayableContainer.press(self, key):
			return

		kbuf = self.env.keybuffer
		cmd = kbuf.command

		if kbuf.failure:
			kbuf.clear()
			return
		elif not cmd:
			return

		self.env.cmd = cmd

		if cmd.function:
			try:
				cmd.function(CommandArgs.from_widget(self))
			except Exception as error:
				self.fm.notify(error)
			if kbuf.done:
				kbuf.clear()
		else:
			kbuf.clear()

	def get_next_key(self):
		"""Waits for key input and returns the pressed key"""
		key = self.win.getch()
		if key is not -1:
			if self.settings.flushinput:
				curses.flushinp()
		return key

	def setup(self):
		"""
		Called after an initialize() call.
		Override this!
		"""

	def redraw(self):
		"""Redraw all widgets"""
		self.poke()
		self.draw()
		self.finalize()

	def redraw_window(self):
		"""Redraw the window. This only calls self.win.redrawwin()."""
		self.win.erase()
		self.win.redrawwin()
		self.win.refresh()
		self.win.redrawwin()
		self.need_redraw = True

	def update_size(self):
		"""
		Update self.env.termsize.
		Extend this method to resize all widgets!
		"""
		self.env.termsize = self.win.getmaxyx()

	def draw(self):
		"""Erase the window, then draw all objects in the container"""
		self.win.touchwin()
		DisplayableContainer.draw(self)
		if self.settings.update_title:
			hostname = str(socket.gethostname())
			try:
				cwd = self.fm.env.pwd.path
			except:
				cwd = ' - ranger'
			sys.stdout.write("\033]2;" + hostname + cwd + "\007")
		self.win.refresh()

	def finalize(self):
		"""Finalize every object in container and refresh the window"""
		DisplayableContainer.finalize(self)
		self.win.refresh()
