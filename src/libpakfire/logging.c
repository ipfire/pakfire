/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2017 Pakfire development team                                 #
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
#############################################################################*/

#include <stdarg.h>
#include <stdio.h>
#include <syslog.h>

#include <pakfire/private.h>

PAKFIRE_EXPORT void pakfire_log_stderr(int priority, const char* file,
		int line, const char* fn, const char* format, va_list args) {
	fprintf(stderr, "pakfire: ");

	// Optionally log the function name
	if (fn)
		fprintf(stderr, "%s: ", fn);

	vfprintf(stderr, format, args);
}

PAKFIRE_EXPORT void pakfire_log_syslog(int priority, const char* file,
		int line, const char* fn, const char* format, va_list args) {
	openlog("pakfire", LOG_PID, LOG_DAEMON);
	vsyslog(priority | LOG_DAEMON, format, args);
}
