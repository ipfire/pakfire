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

import sys

from . import progressbar

def make_progress(message, maxval, eta=True, speed=False):
	# Return nothing if stdout is not a terminal.
	if not sys.stdout.isatty():
		return

	if not maxval:
		maxval = 1

	pb = progressbar.ProgressBar(maxval)
	pb.add("%-50s" % message)

	bar = progressbar.WidgetBar()
	pb.add(bar)

	if speed:
		percentage = progressbar.WidgetPercentage()
		pb.add(percentage)

		filetransfer = progressbar.WidgetFileTransferSpeed()
		pb.add(filetransfer)

	if eta:
		eta = progressbar.WidgetETA()
		pb.add(eta)

	return pb.start()
