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

#ifndef PAKFIRE_LOGGING_H
#define PAKFIRE_LOGGING_H

#include <pakfire/types.h>

void pakfire_log_stderr(Pakfire pakfire, int priority, const char* file,
		int line, const char* fn, const char* format, va_list args);
void pakfire_log_syslog(Pakfire pakfire, int priority, const char* file,
		int line, const char* fn, const char* format, va_list args);

#ifdef PAKFIRE_PRIVATE

void pakfire_log(Pakfire pakfire, int priority, const char *file,
	int line, const char *fn, const char *format, ...)
	__attribute__((format(printf, 6, 7)));

// This function does absolutely nothing
static inline void __attribute__((always_inline, format(printf, 2, 3)))
	pakfire_log_null(Pakfire pakfire, const char *format, ...) {}

#define pakfire_log_condition(pakfire, prio, arg...) \
	do { \
		if (pakfire_get_log_priority(pakfire) >= prio) \
			pakfire_log(pakfire, prio, __FILE__, __LINE__, __FUNCTION__, ## arg); \
	} while (0)

#define INFO(pakfire, arg...) pakfire_log_condition(pakfire, LOG_INFO, ## arg)
#define ERROR(pakfire, arg...) pakfire_log_condition(pakfire, LOG_ERR, ## arg)

#ifdef ENABLE_DEBUG
#	define DEBUG(pakfire, arg...) pakfire_log_condition(pakfire, LOG_DEBUG, ## arg)
#else
#	define DEBUG(pakfire, arg...) pakfire_log_null(pakfire, ## arg)
#endif

#endif /* PAKFIRE_PRIVATE */
#endif /* PAKFIRE_LOGGING_H */
