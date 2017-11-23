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

#ifndef PAKFIRE_KEY_H
#define PAKFIRE_KEY_H

#include <gpgme.h>

#include <pakfire/types.h>

typedef enum pakfire_key_export_mode {
	PAKFIRE_KEY_EXPORT_MODE_PUBLIC = 0,
	PAKFIRE_KEY_EXPORT_MODE_SECRET,
} pakfire_key_export_mode_t;

PakfireKey* pakfire_key_list(Pakfire pakfire);

PakfireKey pakfire_key_create(Pakfire pakfire, gpgme_key_t gpgkey);
PakfireKey pakfire_key_ref(PakfireKey key);
void pakfire_key_unref(PakfireKey key);

PakfireKey pakfire_key_get(Pakfire pakfire, const char* fingerprint);
const char* pakfire_key_get_fingerprint(PakfireKey key);
PakfireKey pakfire_key_generate(Pakfire pakfire, const char* userid);
char* pakfire_key_export(PakfireKey key, pakfire_key_export_mode_t mode);
PakfireKey* pakfire_key_import(Pakfire pakfire, const char* data);

#ifdef PAKFIRE_PRIVATE

struct _PakfireKey {
	Pakfire pakfire;
	gpgme_key_t gpgkey;
	int nrefs;
};

#endif

#endif /* PAKFIRE_KEY_H */
