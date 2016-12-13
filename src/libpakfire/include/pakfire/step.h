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

#include <pakfire/types.h>

PakfireStep pakfire_step_create(PakfireTransaction transaction, Id id);
void pakfire_step_free(PakfireStep step);

PakfirePackage pakfire_step_get_package(PakfireStep step);
int pakfire_step_get_type(PakfireStep step);
const char* pakfire_step_get_type_string(PakfireStep step);

unsigned long long pakfire_step_get_downloadsize(PakfireStep step);
long pakfire_step_get_installsizechange(PakfireStep step);

int pakfire_step_needs_download(PakfireStep step);

#ifdef PAKFIRE_PRIVATE

struct _PakfireStep {
	PakfirePool pool;
	PakfireTransaction transaction;
	Id id;
};

static inline PakfirePool pakfire_step_pool(PakfireStep step) {
	return step->pool;
}

#endif

#endif /* PAKFIRE_STEP_H */
