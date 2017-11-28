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
#include <stdlib.h>
#include <string.h>
#include <syslog.h>

#include <pakfire/pakfire.h>
#include <pakfire/pool.h>
#include <pakfire/system.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

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

Pakfire pakfire_create(const char* path, const char* arch) {
	Pakfire pakfire = pakfire_calloc(1, sizeof(*pakfire));
	if (pakfire) {
		pakfire->nrefs = 1;

		pakfire->path = pakfire_strdup(path);
		if (!arch) {
			arch = system_machine();
		}
		pakfire->arch = pakfire_strdup(arch);

		// Setup logging
		pakfire->log_function = pakfire_log_syslog;
		pakfire->log_priority = LOG_ERR;

		const char* priority = secure_getenv("PAKFIRE_LOG");
		if (priority)
			pakfire_set_log_priority(pakfire, log_priority(priority));

		DEBUG(pakfire, "Pakfire initialized at %p\n", pakfire);
		DEBUG(pakfire, "  arch = %s\n", pakfire->arch);
		DEBUG(pakfire, "  path = %s\n", pakfire->path);

		// Initialize the pool
		pakfire->pool = pakfire_pool_create(pakfire);
	}

	return pakfire;
}

Pakfire pakfire_ref(Pakfire pakfire) {
	++pakfire->nrefs;

	return pakfire;
}

void pakfire_unref(Pakfire pakfire) {
	if (--pakfire->nrefs > 0)
		return;

	pakfire_pool_unref(pakfire->pool);

	pakfire_free(pakfire->path);
	pakfire_free(pakfire->arch);

	DEBUG(pakfire, "Pakfire released at %p\n", pakfire);
	pakfire_free(pakfire);
}

pakfire_log_function_t pakfire_get_log_function(Pakfire pakfire) {
	return pakfire->log_function;
}

void pakfire_set_log_function(Pakfire pakfire, pakfire_log_function_t func) {
	pakfire->log_function = func;
}

int pakfire_get_log_priority(Pakfire pakfire) {
	return pakfire->log_priority;
}

void pakfire_set_log_priority(Pakfire pakfire, int priority) {
	pakfire->log_priority = priority;
}

const char* pakfire_get_path(Pakfire pakfire) {
	return pakfire->path;
}

const char* pakfire_get_arch(Pakfire pakfire) {
	return pakfire->arch;
}

PakfirePool pakfire_get_pool(Pakfire pakfire) {
	return pakfire_pool_ref(pakfire->pool);
}
