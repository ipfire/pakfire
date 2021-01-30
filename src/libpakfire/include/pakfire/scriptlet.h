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

#ifndef PAKFIRE_SCRIPTLET_H
#define PAKFIRE_SCRIPTLET_H

// This is an internal data structure

#ifdef PAKFIRE_PRIVATE

#include <pakfire/types.h>

typedef enum _pakfire_script_types {
	PAKFIRE_SCRIPTLET_UNDEFINED = 0,
	PAKFIRE_SCRIPTLET_PREIN,
	PAKFIRE_SCRIPTLET_PREUN,
	PAKFIRE_SCRIPTLET_PREUP,
	PAKFIRE_SCRIPTLET_PRETRANSIN,
	PAKFIRE_SCRIPTLET_PRETRANSUN,
	PAKFIRE_SCRIPTLET_PRETRANSUP,
	PAKFIRE_SCRIPTLET_POSTIN,
	PAKFIRE_SCRIPTLET_POSTUN,
	PAKFIRE_SCRIPTLET_POSTUP,
	PAKFIRE_SCRIPTLET_POSTTRANSIN,
	PAKFIRE_SCRIPTLET_POSTTRANSUN,
	PAKFIRE_SCRIPTLET_POSTTRANSUP,
} pakfire_scriptlet_type;

struct pakfire_scriptlet {
	pakfire_scriptlet_type type;
	void* data;
	size_t size;
};

struct pakfire_scriptlet* pakfire_scriptlet_create(Pakfire pakfire);
void pakfire_scriptlet_free(struct pakfire_scriptlet* scriptlet);

pakfire_scriptlet_type pakfire_scriptlet_type_from_filename(const char* filename);

#endif

#endif /* PAKFIRE_SCRIPTLET_H */
