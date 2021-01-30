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
	if (strcmp(filename, "scriptlets/prein") == 0)
		return PAKFIRE_SCRIPTLET_PREIN;

	else if (strcmp(filename, "scriptlets/preun") == 0)
		return PAKFIRE_SCRIPTLET_PREUN;

	else if (strcmp(filename, "scriptlets/preup") == 0)
		return PAKFIRE_SCRIPTLET_PREUP;

	else if (strcmp(filename, "scriptlets/postin") == 0)
		return PAKFIRE_SCRIPTLET_POSTIN;

	else if (strcmp(filename, "scriptlets/postun") == 0)
		return PAKFIRE_SCRIPTLET_POSTUN;

	else if (strcmp(filename, "scriptlets/postup") == 0)
		return PAKFIRE_SCRIPTLET_POSTUP;

	else if (strcmp(filename, "scriptlets/pretransin") == 0)
		return PAKFIRE_SCRIPTLET_PRETRANSIN;

	else if (strcmp(filename, "scriptlets/pretransun") == 0)
		return PAKFIRE_SCRIPTLET_PRETRANSUN;

	else if (strcmp(filename, "scriptlets/pretransup") == 0)
		return PAKFIRE_SCRIPTLET_PRETRANSUP;

	else if (strcmp(filename, "scriptlets/posttransin") == 0)
		return PAKFIRE_SCRIPTLET_POSTTRANSIN;

	else if (strcmp(filename, "scriptlets/posttransun") == 0)
		return PAKFIRE_SCRIPTLET_POSTTRANSUN;

	else if (strcmp(filename, "scriptlets/posttransup") == 0)
		return PAKFIRE_SCRIPTLET_POSTTRANSUP;

	return PAKFIRE_SCRIPTLET_UNDEFINED;
}

static const char* pakfire_step_script_filename(pakfire_scriptlet_type script) {
	switch (script) {
		case PAKFIRE_SCRIPTLET_PREIN:
			return "scriptlets/prein";

		case PAKFIRE_SCRIPTLET_PREUN:
			return "scriptlets/preun";

		case PAKFIRE_SCRIPTLET_PREUP:
			return "scriptlets/preup";

		case PAKFIRE_SCRIPTLET_PRETRANSIN:
			return "scriptlets/pretansin";

		case PAKFIRE_SCRIPTLET_PRETRANSUN:
			return "scriptlets/pretransun";

		case PAKFIRE_SCRIPTLET_PRETRANSUP:
			return "scriptlets/pretransup";

		case PAKFIRE_SCRIPTLET_POSTIN:
			return "scriptlets/postin";

		case PAKFIRE_SCRIPTLET_POSTUN:
			return "scriptlets/postun";

		case PAKFIRE_SCRIPTLET_POSTUP:
			return "scriptlets/postup";

		case PAKFIRE_SCRIPTLET_POSTTRANSIN:
			return "scriptlets/posttransin";

		case PAKFIRE_SCRIPTLET_POSTTRANSUN:
			return "scriptlets/posttransun";

		case PAKFIRE_SCRIPTLET_POSTTRANSUP:
			return "scriptlets/posttransup";
	}

	return NULL;
}
