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

#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>

#include <pakfire/logging.h>
#include <pakfire/pakfire.h>

static pakfire_logging_config_t conf = {
	.function = pakfire_log_syslog,
	.priority = LOG_ERR,
};

static int log_priority(const char* priority) {
	char* end;

	int prio = strtol(priority, &end, 10);
	if (*end == '\0' || isspace(*end))
		return prio;

	if (strncmp(priority, "error", strlen("error")) == 0)
		return LOG_ERR;

	if (strncmp(priority, "info", strlen("info")) == 0)
		return LOG_INFO;

	if (strncmp(priority, "debug", strlen("debug")) == 0)
		return LOG_DEBUG;

	return 0;
}

void pakfire_setup_logging() {
	const char* priority = secure_getenv("PAKFIRE_LOG");
	if (priority)
		pakfire_log_set_priority(log_priority(priority));
}

pakfire_log_function_t pakfire_log_get_function() {
	return conf.function;
}

void pakfire_log_set_function(pakfire_log_function_t func) {
	conf.function = func;
}

int pakfire_log_get_priority() {
	return conf.priority;
}

void pakfire_log_set_priority(int priority) {
	conf.priority = priority;
}

void pakfire_log(int priority, const char* file, int line,
		const char* fn, const char* format, ...) {
	va_list args;

	// Save errno
	int saved_errno = errno;

	va_start(args, format);
	conf.function(priority, file, line, fn, format, args);
	va_end(args);

	// Restore errno
	errno = saved_errno;
}

void pakfire_log_stderr(int priority, const char* file,
		int line, const char* fn, const char* format, va_list args) {
	fprintf(stderr, "pakfire: %s: ", fn);
	vfprintf(stderr, format, args);
}

void pakfire_log_syslog(int priority, const char* file,
		int line, const char* fn, const char* format, va_list args) {
	openlog("pakfire", LOG_PID, LOG_DAEMON);
	vsyslog(priority | LOG_DAEMON, format, args);
}
