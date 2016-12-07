#!/usr/bin/python3
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2013 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import datetime
import math
import signal
import struct
import sys
import time

from ..i18n import _

from . import helpers

DEFAULT_VALUE_MAX = 100
DEFAULT_TERM_WIDTH = 80

class ProgressBar(object):
	def __init__(self, value_max=None):
		self.value_max = value_max or DEFAULT_VALUE_MAX
		self.value_cur = 0

		self.time_start = None
		self.finished = False
		self.error = None

		# Use the error console as default output.
		self.fd = sys.stderr

		# Determine the width of the terminal.
		self.term_width = self.get_terminal_width()
		self.register_terminal_resize_signal()

		self.widgets = []

		# Update at max. every poll seconds.
		self.poll = 0.5

	def add(self, widget):
		self.widgets.append(widget)

	def reset(self):
		"""
			Resets the progress bar to start
		"""
		self.start()

	def start(self):
		self.num_intervals = max(self.term_width, 100)
		self.next_update = 0
		self.update_interval = self.value_max / self.num_intervals

		# Save the time when we started.
		self.time_start = self.time_last_updated = time.time()

		# Initialize the bar.
		self.update(0)

		return self

	def finish(self, error=None):
		if self.finished:
			return

		self.finished = True

		# Save an exception we could print
		self.error = error

		# Complete the progress bar.
		self.update(self.value_max)

		# End the line.
		self.fd.write("\n")

		self.unregister_terminal_resize_signal()

	def update(self, value):
		if not self.time_start:
			raise RuntimeError("You need to execute start() first")

		self.value_cur = value

		if not self._need_update():
			return

		self.next_update = self.value_cur + self.update_interval
		self.last_update_time = time.time()

		self.fd.write(self._format_line())
		self.fd.write("\r")

	def increment(self, value):
		return self.update(self.value_cur + value)

	def _need_update(self):
		if self.value_cur >= self.next_update or self.finished:
			return True

		delta = time.time() - self.last_update_time
		return delta > self.poll

	def _format_line(self):
		result = []
		expandables = []

		width = self.term_width - (len(self.widgets) - 1) - 4

		for index, widget in enumerate(self.widgets):
			if isinstance(widget, Widget) and widget.expandable:
				result.append(widget)
				expandables.append(index)
				continue

			widget = format_updatable(widget, self)
			result.append(widget)

			# Subtract the consumed space by this widget
			width -= len(widget)

		while expandables:
			portion = int(math.ceil(width / len(expandables)))
			index = expandables.pop()

			widget = result[index].update(self, portion)
			result[index] = widget

			# Subtract the consumed space by this widget
			width -= len(widget)

		return "  %s  " % " ".join(result)

	def get_terminal_width(self):
		cr = helpers.ioctl_GWINSZ(self.fd)
		if cr:
			return cr[1]

		# If the ioctl command failed, use the environment data.
		columns = os.environ.get("COLUMNS", None)
		try:
			return int(columns) - 1
		except (TypeError, ValueError):
			pass

		return DEFAULT_TERM_WIDTH

	def handle_terminal_resize(self, *args, **kwargs):
		"""
			Catches terminal resize signals.
		"""
		self.term_width = self.get_terminal_width()

	def register_terminal_resize_signal(self):
		signal.signal(signal.SIGWINCH, self.handle_terminal_resize)

	def unregister_terminal_resize_signal(self):
		signal.signal(signal.SIGWINCH, signal.SIG_DFL)

	@property
	def percentage(self):
		if self.value_cur >= self.value_max:
			return 100.0

		return self.value_cur * 100.0 / self.value_max

	@property
	def seconds_elapsed(self):
		if self.time_start:
			return time.time() - self.time_start

		return 0

	# Implement using progressbar as context

	def __enter__(self):
		# Start the progressbar
		self.start()

		return self

	def __exit__(self, type, value, traceback):
		self.finish(error=value)


def format_updatable(widget, pbar):
	if hasattr(widget, "update"):
		return widget.update(pbar)

	return widget


class Widget(object):
	expandable = False

	def update(self, pbar):
		pass


class WidgetError(Widget):
	def update(self, pbar):
		if pbar.finished and pbar.error:
			return _("Error: %s") % pbar.error

		return ""


class WidgetFill(Widget):
	expandable = True

	def update(self, pbar, width):
		return "#" * width


class WidgetTimer(Widget):
	def __init__(self, format_string=None):
		if format_string is None:
			format_string = _("Elapsed Time: %s")

		self.format_string = format_string

	@staticmethod
	def format_time(seconds):
		try:
			seconds = int(seconds)
		except ValueError:
			pass

		return "%s" % datetime.timedelta(seconds=seconds)

	def update(self, pbar):
		return self.format_string % self.format_time(pbar.seconds_elapsed)


class WidgetETA(WidgetTimer):
	def update(self, pbar):
		fmt = "%-5s: %s"

		if pbar.value_cur == 0:
			return fmt % (_("ETA"), "--:--:--")

		elif pbar.finished:
			return fmt % (_("Time"), self.format_time(pbar.seconds_elapsed))

		else:
			eta = pbar.seconds_elapsed * pbar.value_max / pbar.value_cur - pbar.seconds_elapsed
			return fmt % (_("ETA"), self.format_time(eta))


class WidgetAnimatedMarker(Widget):
	def __init__(self):
		self.markers = "|/-\\"
		self.marker_cur = -1

	def update(self, pbar):
		if pbar.finished:
			return self.markers[0]

		self.marker_cur = (self.marker_cur + 1) % len(self.markers)
		return self.markers[self.marker_cur]


class WidgetCounter(Widget):
	def __init__(self, format_string="%d"):
		self.format_string = format_string

	def update(self, pbar):
		return self.format_string % pbar.value_cur


class WidgetPercentage(Widget):
	def __init__(self, clear_when_finished=False):
		self.clear_when_finished = clear_when_finished

	def update(self, pbar):
		if self.clear_when_finished and pbar.finished:
			return ""

		return "%3d%%" % pbar.percentage


class WidgetBar(WidgetFill):
	def __init__(self):
		self.marker = "#"
		self.marker_inactive = "-"

		self.marker_left = "["
		self.marker_right = "]"

	def update(self, pbar, width):
		# Clear the screen if the progress has finished.
		if pbar.finished:
			return " " * width

		marker_left, marker, marker_inactive, marker_right = (format_updatable(w, pbar)
			for w in (self.marker_left, self.marker, self.marker_inactive, self.marker_right))

		width -= len(marker_left) + len(marker_right)

		if pbar.value_max:
			marker *= pbar.value_cur * width // pbar.value_max
		else:
			marker = ""

		return "".join((marker_left, marker.ljust(width, marker_inactive), marker_right))


class WidgetFileTransferSpeed(Widget):
	def update(self, pbar):
		speed = 0

		if pbar.seconds_elapsed >= 1 and pbar.value_cur > 0:
			speed = pbar.value_cur / pbar.seconds_elapsed

		return helpers.format_speed(speed)


class WidgetBytesReceived(Widget):
	def update(self, pbar):
		return helpers.format_size(pbar.value_cur)


if __name__ == "__main__":
	pbar = ProgressBar(100)

	counter = WidgetCounter()
	pbar.add(counter)

	timer = WidgetTimer()
	pbar.add(timer)

	bar = WidgetBar()
	pbar.add(bar)

	fill = WidgetFill()
	pbar.add(fill)

	eta = WidgetETA()
	pbar.add(eta)

	percentage = WidgetPercentage()
	pbar.add(percentage)

	speed = WidgetFileTransferSpeed()
	pbar.add(speed)

	pbar.start()

	for i in range(100):
		pbar.update(i)
		time.sleep(0.25)

	pbar.finish()
