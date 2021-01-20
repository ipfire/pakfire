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

#include <sqlite3.h>

#include <pakfire/db.h>
#include <pakfire/logging.h>
#include <pakfire/pakfire.h>
#include <pakfire/private.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define DATABASE_PATH PAKFIRE_PRIVATE_DIR "/packages.db"

struct pakfire_db {
	Pakfire pakfire;
	int nrefs;

	int mode;

	sqlite3* handle;
};

static void logging_callback(void* data, int r, const char* msg) {
	Pakfire pakfire = (Pakfire)data;

	ERROR(pakfire, "Database Error: %s: %s\n",
		sqlite3_errstr(r), msg);
}

static void pakfire_db_free(struct pakfire_db* db) {
	DEBUG(db->pakfire, "Releasing database at %p\n", db);

	// Close database handle
	if (db->handle) {
		int r = sqlite3_close(db->handle);
		if (r != SQLITE_OK) {
			ERROR(db->pakfire, "Could not close database handle: %s\n",
				sqlite3_errmsg(db->handle));
		}
	}

	pakfire_unref(db->pakfire);

	pakfire_free(db);
}

static int pakfire_db_setup(struct pakfire_db* db) {
	// Setup logging
	sqlite3_config(SQLITE_CONFIG_LOG, logging_callback, db->pakfire);

	// Done when not in read-write mode
	if (db->mode != PAKFIRE_DB_READWRITE)
		return 0;

	// XXX Create schema

	return 0;
}

PAKFIRE_EXPORT int pakfire_db_open(struct pakfire_db** db, Pakfire pakfire, int flags) {
	int r = 1;

	struct pakfire_db* o = pakfire_calloc(1, sizeof(*o));
	if (!o)
		return -ENOMEM;

	DEBUG(pakfire, "Allocated database at %p\n", o);

	o->pakfire = pakfire_ref(pakfire);
	o->nrefs = 1;

	int sqlite3_flags = 0;

	// Store mode & forward it to sqlite3
	if (flags & PAKFIRE_DB_READWRITE) {
		o->mode = PAKFIRE_DB_READWRITE;
		sqlite3_flags |= SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE;
	} else {
		o->mode = PAKFIRE_DB_READONLY;
		sqlite3_flags |= SQLITE_OPEN_READONLY;
	}

	// Make the filename
	char* path = pakfire_make_path(o->pakfire, DATABASE_PATH);
	if (!path)
		goto END;

	// Try to open the sqlite3 database file
	r = sqlite3_open_v2(path, &o->handle, sqlite3_flags, NULL);
	if (r != SQLITE_OK) {
		ERROR(pakfire, "Could not open database %s: %s\n",
			path, sqlite3_errmsg(o->handle));

		r = 1;
		goto END;
	}

	// Setup the database
	r = pakfire_db_setup(o);
	if (r)
		goto END;

	*db = o;
	r = 0;

END:
	if (r)
		pakfire_db_free(o);

	if (path)
		free(path);

	return r;
}

PAKFIRE_EXPORT struct pakfire_db* pakfire_db_ref(struct pakfire_db* db) {
	db->nrefs++;

	return db;
}

PAKFIRE_EXPORT struct pakfire_db* pakfire_db_unref(struct pakfire_db* db) {
	if (--db->nrefs > 0)
		return db;

	pakfire_db_free(db);

	return NULL;
}

PAKFIRE_EXPORT int pakfire_db_add_package(struct pakfire_db* db, PakfirePackage pkg) {
	return 0; // TODO
}

PAKFIRE_EXPORT int pakfire_db_remove_package(struct pakfire_db* db, PakfirePackage pkg) {
	return 0; // TODO
}
