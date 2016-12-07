#!/usr/bin/python3
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2016 Pakfire development team                                 #
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

import fcntl
import struct
import termios

def ioctl_GWINSZ(fd):
	try:
		return struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))
	except:
		pass

def terminal_size():
	cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

	if not cr:
		try:
			fd = os.open(os.ctermid(), os.O_RDONLY)
			cr = ioctl_GWINSZ(fd)
			os.close(fd)
		except:
			pass

	if not cr:
		try:
			cr = (os.environ["LINES"], os.environ["COLUMNS"])
		except:
			cr = (25, 80)

	return int(cr[1]), int(cr[0])

def format_size(s):
	units = (
		"%4.0f ",
		"%4.0fk",
		"%4.1fM",
		"%4.1fG",
	)
	unit = 0

	while abs(s) >= 1024 and unit < len(units):
		s /= 1024
		unit += 1

	return units[unit] % s

def format_time(s):
	return "%02d:%02d" % (s // 60, s % 60)

def format_speed(s):
	return "%sB/s" % format_size(s)
