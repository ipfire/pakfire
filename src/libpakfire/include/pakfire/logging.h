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

#include <syslog.h>

#include <pakfire/types.h>

void pakfire_log_stderr(int priority, const char* file,
		int line, const char* fn, const char* format, va_list args);
void pakfire_log_syslog(int priority, const char* file,
		int line, const char* fn, const char* format, va_list args);

pakfire_log_function_t pakfire_log_get_function();
void pakfire_log_set_function(pakfire_log_function_t func);
int pakfire_log_get_priority();
void pakfire_log_set_priority(int priority);

void pakfire_log_stderr(int priority, const char* file,
	int line, const char* fn, const char* format, va_list args);
void pakfire_log_syslog(int priority, const char* file,
	int line, const char* fn, const char* format, va_list args);

#ifdef PAKFIRE_PRIVATE

typedef struct pakfire_logging_config {
	pakfire_log_function_t function;
	int priority;
} pakfire_logging_config_t;

void pakfire_setup_logging();
void pakfire_log(int priority, const char *file,
	int line, const char *fn, const char *format, ...)
	__attribute__((format(printf, 5, 6)));

// This function does absolutely nothing
static inline void __attribute__((always_inline, format(printf, 1, 2)))
	pakfire_log_null(const char *format, ...) {}

#define pakfire_log_condition(prio, arg...) \
	do { \
		if (pakfire_log_get_priority() >= prio) \
			pakfire_log(prio, __FILE__, __LINE__, __FUNCTION__, ## arg); \
	} while (0)

#define INFO(arg...) pakfire_log_condition(LOG_INFO, ## arg)
#define ERROR(arg...) pakfire_log_condition(LOG_ERR, ## arg)

#ifdef ENABLE_DEBUG
#	define DEBUG(arg...) pakfire_log_condition(LOG_DEBUG, ## arg)
#else
#	define DEBUG pakfire_log_null
#endif

#endif /* PAKFIRE_PRIVATE */
#endif /* PAKFIRE_LOGGING_H */
