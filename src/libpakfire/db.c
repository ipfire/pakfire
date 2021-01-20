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

#include <errno.h>
#include <stdlib.h>

#include <pakfire/db.h>
#include <pakfire/pakfire.h>
#include <pakfire/logging.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define DATABASE_PATH PAKFIRE_PRIVATE_DIR "/packages.db"

struct pakfire_db {
	Pakfire pakfire;
	int nrefs;
};

int pakfire_db_open(struct pakfire_db** db, Pakfire pakfire) {
	struct pakfire_db* o = pakfire_calloc(1, sizeof(*o));
	if (!o)
		return -ENOMEM;

	DEBUG(pakfire, "Allocated database at %p\n", o);

	o->pakfire = pakfire_ref(pakfire);
	o->nrefs = 1;

	*db = o;

	return 0;
}

struct pakfire_db* pakfire_db_ref(struct pakfire_db* db) {
	db->nrefs++;

	return db;
}

static void pakfire_db_free(struct pakfire_db* db) {
	DEBUG(db->pakfire, "Releasing database at %p\n", db);

	pakfire_unref(db->pakfire);

	pakfire_free(db);
}

struct pakfire_db* pakfire_db_unref(struct pakfire_db* db) {
	if (--db->nrefs > 0)
		return db;

	pakfire_db_free(db);

	return NULL;
}

int pakfire_db_add_package(struct pakfire_db* db, PakfirePackage pkg) {
	return 0; // TODO
}

int pakfire_db_remove_package(struct pakfire_db* db, PakfirePackage pkg) {
	return 0; // TODO
}
