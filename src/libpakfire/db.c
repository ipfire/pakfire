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

#include <lmdb.h>

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

/*
	This function initialises the database environment, but stores it in the main pakfire
	object so that we do not have to create a circle-reference between pakfire and the
	database object.
*/
int pakfire_db_env_init(Pakfire pakfire, MDB_env** env) {
	DEBUG(pakfire, "Initialising database environment\n");

	// Allocate database environment
	int r = mdb_env_create(env);
	if (r) {
		ERROR(pakfire, "Could not allocate database environment\n");
		return r;
	}

	// The database path
	char* path = pakfire_make_path(pakfire, DATABASE_PATH);

	// Open the database environment
	r = mdb_env_open(*env, path, MDB_NOSUBDIR, 0660);
	if (r) {
		switch (r) {
			case MDB_VERSION_MISMATCH:
				ERROR(pakfire, "The database is of an incompatible version\n");
				errno = EINVAL;
				break;

			case MDB_INVALID:
				errno = EINVAL;
				break;

			default:
				ERROR(pakfire, "Could not open database %s: %s\n", path, strerror(errno));
				errno = r;
		}

		// Reset r to non-zero
		r = 1;
		goto ERROR;
	}

ERROR:
	free(path);

	return r;
}

void pakfire_db_env_free(Pakfire pakfire, MDB_env* env) {
	DEBUG(pakfire, "Freeing database environment\n");

	if (env)
		mdb_env_close(env);
}

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
