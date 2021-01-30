/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2021 Pakfire development team                                 #
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

#include <stdlib.h>
#include <string.h>

#include <pakfire/logging.h>
#include <pakfire/scriptlet.h>
#include <pakfire/types.h>

struct pakfire_scriptlet_type PAKFIRE_SCRIPTLET_TYPES[NUM_PAKFIRE_SCRIPTLET_TYPES + 1] = {
	{ PAKFIRE_SCRIPTLET_PREIN,       "scriptlets/prein",       "prein" },
	{ PAKFIRE_SCRIPTLET_PREUN,       "scriptlets/preun",       "preun" },
	{ PAKFIRE_SCRIPTLET_PREUP,       "scriptlets/preup",       "preup" },
	{ PAKFIRE_SCRIPTLET_POSTIN,      "scriptlets/postin",      "postin" },
	{ PAKFIRE_SCRIPTLET_POSTUN,      "scriptlets/postun",      "postun" },
	{ PAKFIRE_SCRIPTLET_POSTUP,      "scriptlets/postup",      "postup" },
	{ PAKFIRE_SCRIPTLET_PRETRANSIN,  "scriptlets/pretransin",  "pretransin" },
	{ PAKFIRE_SCRIPTLET_PRETRANSUN,  "scriptlets/pretransun",  "pretransun" },
	{ PAKFIRE_SCRIPTLET_PRETRANSUP,  "scriptlets/pretransup",  "pretransup" },
	{ PAKFIRE_SCRIPTLET_POSTTRANSIN, "scriptlets/posttransin", "posttransin" },
	{ PAKFIRE_SCRIPTLET_POSTTRANSUN, "scriptlets/posttransun", "posttransun" },
	{ PAKFIRE_SCRIPTLET_POSTTRANSUP, "scriptlets/posttransup", "posttransup" },
	{ PAKFIRE_SCRIPTLET_UNDEFINED,   NULL,                     NULL },
};

struct pakfire_scriptlet* pakfire_scriptlet_create(Pakfire pakfire) {
	struct pakfire_scriptlet* scriptlet = calloc(1, sizeof(*scriptlet));
	if (!scriptlet)
		return NULL;

	DEBUG(pakfire, "Allocated scriptlet at %p\n", scriptlet);

	return scriptlet;
};

void pakfire_scriptlet_free(struct pakfire_scriptlet* scriptlet) {
	if (scriptlet->data)
		free(scriptlet->data);

	free(scriptlet);
}

pakfire_scriptlet_type pakfire_scriptlet_type_from_filename(const char* filename) {
	struct pakfire_scriptlet_type* t = PAKFIRE_SCRIPTLET_TYPES;

	while (t->type) {
		if (strcmp(t->filename, filename) == 0)
			return t->type;

		t++;
	}

	return PAKFIRE_SCRIPTLET_UNDEFINED;
}

const char* pakfire_scriptlet_handle_from_type(pakfire_scriptlet_type type) {
	struct pakfire_scriptlet_type* t = PAKFIRE_SCRIPTLET_TYPES;

	while (t->type) {
		if (t->type == type)
			return t->handle;

		t++;
	}

	return NULL;
}
