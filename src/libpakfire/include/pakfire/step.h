/*#############################################################################
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
#############################################################################*/

#ifndef PAKFIRE_STEP_H
#define PAKFIRE_STEP_H

#include <solv/pooltypes.h>

#include <pakfire/transaction.h>
#include <pakfire/types.h>

typedef enum _pakfire_step_types {
	PAKFIRE_STEP_IGNORE = 0,
	PAKFIRE_STEP_INSTALL,
	PAKFIRE_STEP_REINSTALL,
	PAKFIRE_STEP_ERASE,
	PAKFIRE_STEP_UPGRADE,
	PAKFIRE_STEP_DOWNGRADE,
	PAKFIRE_STEP_OBSOLETE,
} pakfire_step_type_t;

PakfireStep pakfire_step_create(PakfireTransaction transaction, Id id);
void pakfire_step_free(PakfireStep step);

PakfirePackage pakfire_step_get_package(PakfireStep step);
pakfire_step_type_t pakfire_step_get_type(PakfireStep step);
const char* pakfire_step_get_type_string(PakfireStep step);

unsigned long long pakfire_step_get_downloadsize(PakfireStep step);
long pakfire_step_get_installsizechange(PakfireStep step);

int pakfire_step_needs_download(PakfireStep step);

#ifdef PAKFIRE_PRIVATE

typedef enum _pakfire_script_types {
	PAKFIRE_SCRIPT_PREIN,
	PAKFIRE_SCRIPT_PREUN,
	PAKFIRE_SCRIPT_PREUP,
	PAKFIRE_SCRIPT_PRETRANSIN,
	PAKFIRE_SCRIPT_PRETRANSUN,
	PAKFIRE_SCRIPT_PRETRANSUP,
	PAKFIRE_SCRIPT_POSTIN,
	PAKFIRE_SCRIPT_POSTUN,
	PAKFIRE_SCRIPT_POSTUP,
	PAKFIRE_SCRIPT_POSTTRANSIN,
	PAKFIRE_SCRIPT_POSTTRANSUN,
	PAKFIRE_SCRIPT_POSTTRANSUP,
} pakfire_script_type;

struct _PakfireStep {
	PakfirePool pool;
	PakfireTransaction transaction;
	Id id;
};

static inline PakfirePool pakfire_step_pool(PakfireStep step) {
	return step->pool;
}

int pakfire_step_run(PakfireStep step, pakfire_action_type action);

#endif

#endif /* PAKFIRE_STEP_H */
