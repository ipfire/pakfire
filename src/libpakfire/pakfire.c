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

#include <pakfire/pakfire.h>
#include <pakfire/pool.h>
#include <pakfire/system.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

int pakfire_init() {
	// Setup logging
	pakfire_setup_logging();

	return 0;
}

Pakfire pakfire_create(const char* path, const char* arch) {
	Pakfire pakfire = pakfire_calloc(1, sizeof(*pakfire));
	if (pakfire) {
		pakfire->nrefs = 1;

		pakfire->path = pakfire_strdup(path);
		if (!arch)
			arch = system_machine();
		pakfire->arch = pakfire_strdup(arch);

		DEBUG("Pakfire initialized at %p\n", pakfire);
		DEBUG("  arch = %s\n", pakfire_get_arch(pakfire));
		DEBUG("  path = %s\n", pakfire_get_path(pakfire));

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

	DEBUG("Pakfire released at %p\n", pakfire);
	pakfire_free(pakfire);
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
