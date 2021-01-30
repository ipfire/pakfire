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

#include <pakfire/archive.h>
#include <pakfire/db.h>
#include <pakfire/file.h>
#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/pakfire.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define DATABASE_PATH PAKFIRE_PRIVATE_DIR "/packages.db"

#define CURRENT_SCHEMA 8
#define SCHEMA_MIN_SUP 7

struct pakfire_db {
	Pakfire pakfire;
	int nrefs;

	int mode;

	sqlite3* handle;
	int schema;
};

static void logging_callback(void* data, int r, const char* msg) {
	Pakfire pakfire = (Pakfire)data;

	ERROR(pakfire, "Database Error: %s: %s\n",
		sqlite3_errstr(r), msg);
}

static int pakfire_db_execute(struct pakfire_db* db, const char* stmt) {
	int r;

	DEBUG(db->pakfire, "Executing database query: %s\n", stmt);

	do {
		r = sqlite3_exec(db->handle, stmt, NULL, NULL, NULL);
	} while (r == SQLITE_BUSY);

	// Log any errors
	if (r) {
		ERROR(db->pakfire, "Database query failed: %s\n", sqlite3_errmsg(db->handle));
	}

	return r;
}

static int pakfire_db_begin_transaction(struct pakfire_db* db) {
	return pakfire_db_execute(db, "BEGIN TRANSACTION");
}

static int pakfire_db_commit(struct pakfire_db* db) {
	return pakfire_db_execute(db, "COMMIT");
}

static int pakfire_db_rollback(struct pakfire_db* db) {
	return pakfire_db_execute(db, "ROLLBACK");
}

/*
	This function performs any fast optimization and tries to truncate the WAL log file
	to keep the database as compact as possible on disk.
*/
static void pakfire_db_optimize(struct pakfire_db* db) {
	pakfire_db_execute(db, "PRAGMA optimize");
	pakfire_db_execute(db, "PRAGMA wal_checkpoint = TRUNCATE");
}

static void pakfire_db_free(struct pakfire_db* db) {
	DEBUG(db->pakfire, "Releasing database at %p\n", db);

	if (db->handle) {
		// Optimize the database before it is being closed
		pakfire_db_optimize(db);

		// Close database handle
		int r = sqlite3_close(db->handle);
		if (r != SQLITE_OK) {
			ERROR(db->pakfire, "Could not close database handle: %s\n",
				sqlite3_errmsg(db->handle));
		}
	}

	pakfire_unref(db->pakfire);

	pakfire_free(db);
}

static sqlite3_value* pakfire_db_get(struct pakfire_db* db, const char* key) {
	sqlite3_stmt* stmt = NULL;
	sqlite3_value* val = NULL;
	int r;

	const char* sql = "SELECT val FROM settings WHERE key = ?";

	// Prepare the statement
	r = sqlite3_prepare_v2(db->handle, sql, strlen(sql), &stmt, NULL);
	if (r != SQLITE_OK) {
		//ERROR(db->pakfire, "Could not prepare SQL statement: %s: %s\n",
		//	sql, sqlite3_errmsg(db->handle));
		return NULL;
	}

	// Bind key
	r = sqlite3_bind_text(stmt, 1, key, strlen(key), NULL);
	if (r != SQLITE_OK) {
		ERROR(db->pakfire, "Could not bind key: %s\n", sqlite3_errmsg(db->handle));
		goto ERROR;
	}

	// Execute the statement
	do {
		r = sqlite3_step(stmt);
	} while (r == SQLITE_BUSY);

	// We should have read a row
	if (r != SQLITE_ROW)
		goto ERROR;

	// Read value
	val = sqlite3_column_value(stmt, 0);
	if (!val) {
		ERROR(db->pakfire, "Could not read value\n");
		goto ERROR;
	}

	// Copy value onto the heap
	val = sqlite3_value_dup(val);

ERROR:
	if (stmt)
		sqlite3_finalize(stmt);

	return val;
}

static int pakfire_db_set_int(struct pakfire_db* db, const char* key, int val) {
	sqlite3_stmt* stmt = NULL;
	int r;

	const char* sql = "INSERT INTO settings(key, val) VALUES(?, ?) \
		ON CONFLICT (key) DO UPDATE SET val = excluded.val";

	// Prepare statement
	r = sqlite3_prepare_v2(db->handle, sql, strlen(sql), &stmt, NULL);
	if (r != SQLITE_OK) {
		ERROR(db->pakfire, "Could not prepare SQL statement: %s: %s\n",
			sql, sqlite3_errmsg(db->handle));
		return 1;
	}

	// Bind key
	r = sqlite3_bind_text(stmt, 1, key, strlen(key), NULL);
	if (r != SQLITE_OK) {
		ERROR(db->pakfire, "Could not bind key: %s\n", sqlite3_errmsg(db->handle));
		goto ERROR;
	}

	// Bind val
	r = sqlite3_bind_int64(stmt, 2, val);
	if (r != SQLITE_OK) {
		ERROR(db->pakfire, "Could not bind val: %s\n", sqlite3_errmsg(db->handle));
		goto ERROR;
	}

	// Execute the statement
	do {
		r = sqlite3_step(stmt);
	} while (r == SQLITE_BUSY);

	// Set return code
	r = (r == SQLITE_OK);

ERROR:
	if (stmt)
		sqlite3_finalize(stmt);

	return r;
}

static int pakfire_db_get_schema(struct pakfire_db* db) {
	sqlite3_value* value = pakfire_db_get(db, "schema");
	if (!value)
		return -1;

	int schema = sqlite3_value_int64(value);
	sqlite3_value_free(value);

	DEBUG(db->pakfire, "Database has schema version %d\n", schema);

	return schema;
}

static int pakfire_db_create_schema(struct pakfire_db* db) {
	int r;

	// Create settings table
	r = pakfire_db_execute(db, "CREATE TABLE IF NOT EXISTS settings(key TEXT, val TEXT)");
	if (r)
		return 1;

	// settings: Add a unique index on key
	r = pakfire_db_execute(db, "CREATE UNIQUE INDEX IF NOT EXISTS settings_key ON settings(key)");
	if (r)
		return 1;

	// Create packages table
	r = pakfire_db_execute(db,
		"CREATE TABLE IF NOT EXISTS packages("
			"id             INTEGER PRIMARY KEY, "
			"name           TEXT, "
			"epoch          INTEGER, "
			"version        TEXT, "
			"release        TEXT, "
			"arch           TEXT, "
			"groups         TEXT, "
			"filename       TEXT, "
			"size           INTEGER, "
			"inst_size      INTEGER, "
			"hash1          TEXT, "
			"license        TEXT, "
			"summary        TEXT, "
			"description    TEXT, "
			"uuid           TEXT, "
			"vendor         TEXT, "
			"build_host     TEXT, "
			"build_time     INTEGER, "
			"installed      INTEGER, "
			"reason         TEXT, "
			"repository     TEXT"
		")");
	if (r)
		return 1;

	// packages: Create index to find package by name
	r = pakfire_db_execute(db, "CREATE INDEX IF NOT EXISTS packages_name ON packages(name)");
	if (r)
		return 1;

	// Create dependencies table
	r = pakfire_db_execute(db,
		"CREATE TABLE IF NOT EXISTS dependencies("
			"pkg            INTEGER, "
			"type           TEXT, "
			"dependency     TEXT, "
			"FOREIGN KEY (pkg) REFERENCES packages(id)"
		")");
	if (r)
		return r;

	// dependencies: Add index over packages
	r = pakfire_db_execute(db, "CREATE INDEX IF NOT EXISTS dependencies_pkg_index ON dependencies(pkg)");
	if (r)
		return r;

	// Create files table
	r = pakfire_db_execute(db,
		"CREATE TABLE IF NOT EXISTS files("
			"id             INTEGER PRIMARY KEY, "
			"name           TEXT, "
			"pkg            INTEGER, "
			"size           INTEGER, "
			"type           INTEGER, "
			"config         INTEGER, "
			"datafile       INTEGER, "
			"mode           INTEGER, "
			"user           TEXT, "
			"'group'        TEXT, "
			"hash1          TEXT, "
			"mtime          INTEGER, "
			"capabilities   TEXT, "
			"FOREIGN KEY (pkg) REFERENCES packages(id)"
		")");
	if (r)
		return 1;

	// files: Add index over packages
	r = pakfire_db_execute(db, "CREATE INDEX IF NOT EXISTS files_pkg_index ON files(pkg)");
	if (r)
		return 1;

	// Create scriptlets table
	r = pakfire_db_execute(db,
		"CREATE TABLE IF NOT EXISTS scriptlets("
			"id             INTEGER PRIMARY KEY, "
			"pkg            INTEGER, "
			"action         TEXT, "
			"scriptlet      TEXT, "
			"FOREIGN KEY (pkg) REFERENCES packages(id)"
		")");
	if (r)
		return 1;

	// scriptlets: Add index over packages
	r = pakfire_db_execute(db, "CREATE INDEX IF NOT EXISTS scriptlets_pkg_index ON scriptlets(pkg)");
	if (r)
		return 1;

	return 0;
}

static int pakfire_db_migrate_to_schema_8(struct pakfire_db* db) {
	// packages: Drop build_id column

	// Add foreign keys
	// TODO sqlite doesn't support adding foreign keys to existing tables and so we would
	// need to recreate the whole table and rename it afterwards. Annoying.

	return 0;
}

static int pakfire_db_migrate_schema(struct pakfire_db* db) {
	int r;

	while (db->schema < CURRENT_SCHEMA) {
		// Begin a new transaction
		r = pakfire_db_begin_transaction(db);
		if (r)
			goto ROLLBACK;

		switch (db->schema) {
			// No schema exists
			case -1:
				r = pakfire_db_create_schema(db);
				if (r)
					goto ROLLBACK;

				db->schema = CURRENT_SCHEMA;
				break;

			case 7:
				r = pakfire_db_migrate_to_schema_8(db);
				if (r)
					goto ROLLBACK;

				db->schema++;
				break;

			default:
				ERROR(db->pakfire, "Cannot migrate database from schema %d\n", db->schema);
				goto ROLLBACK;
		}

		// Update the schema version
		r = pakfire_db_set_int(db, "schema", CURRENT_SCHEMA);
		if (r)
			goto ROLLBACK;

		// All done, commit!
		r = pakfire_db_commit(db);
		if (r)
			goto ROLLBACK;
	}

	return 0;

ROLLBACK:
	pakfire_db_rollback(db);

	return 1;
}

static int pakfire_db_setup(struct pakfire_db* db) {
	int r;

	// Setup logging
	sqlite3_config(SQLITE_CONFIG_LOG, logging_callback, db->pakfire);

	// Enable foreign keys
	pakfire_db_execute(db, "PRAGMA foreign_keys = ON");

	// Make LIKE case-sensitive
	pakfire_db_execute(db, "PRAGMA case_sensitive_like = ON");

	// Fetch the current schema
	db->schema = pakfire_db_get_schema(db);

	// Check if the schema is recent enough
	if (db->schema > 0 && db->schema < SCHEMA_MIN_SUP) {
		ERROR(db->pakfire, "Database schema %d is not supported by this version of Pakfire\n",
			db->schema);
		return 1;
	}

	// Done when not in read-write mode
	if (db->mode != PAKFIRE_DB_READWRITE)
		return 0;

	// Disable secure delete
	pakfire_db_execute(db, "PRAGMA secure_delete = OFF");

	// Set database journal to WAL
	r = pakfire_db_execute(db, "PRAGMA journal_mode = WAL");
	if (r != SQLITE_OK) {
		ERROR(db->pakfire, "Could not set journal mode to WAL: %s\n",
			sqlite3_errmsg(db->handle));
		return 1;
	}

	// Disable autocheckpoint
	r = sqlite3_wal_autocheckpoint(db->handle, 0);
	if (r != SQLITE_OK) {
		ERROR(db->pakfire, "Could not disable autocheckpoint: %s\n",
			sqlite3_errmsg(db->handle));
		return 1;
	}

	// Create or migrate schema
	r = pakfire_db_migrate_schema(db);
	if (r)
		return r;

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

static unsigned long pakfire_db_integrity_check(struct pakfire_db* db) {
	sqlite3_stmt* stmt = NULL;
	int r;

	r = sqlite3_prepare_v2(db->handle, "PRAGMA integrity_check", -1, &stmt, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not prepare integrity check: %s\n",
			sqlite3_errmsg(db->handle));
		return 1;
	}

	// Count any errors
	unsigned long errors = 0;

	while (1) {
		do {
			r = sqlite3_step(stmt);
		} while (r == SQLITE_BUSY);

		if (r == SQLITE_ROW) {
			const char* error = (const char*)sqlite3_column_text(stmt, 0);

			// If the message is "ok", the database has passed the check
			if (strcmp(error, "ok") == 0)
				continue;

			// Increment error counter
			errors++;

			// Log the message
			ERROR(db->pakfire, "%s\n", error);

		// Break on anything else
		} else
			break;
	}

	sqlite3_finalize(stmt);

	if (errors)
		ERROR(db->pakfire, "Database integrity check failed\n");
	else
		INFO(db->pakfire, "Database integrity check passed\n");

	return errors;
}

static unsigned long pakfire_db_foreign_key_check(struct pakfire_db* db) {
	sqlite3_stmt* stmt = NULL;
	int r;

	r = sqlite3_prepare_v2(db->handle, "PRAGMA foreign_key_check", -1, &stmt, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not prepare foreign key check: %s\n",
			sqlite3_errmsg(db->handle));
		return 1;
	}

	// Count any errors
	unsigned long errors = 0;

	while (1) {
		do {
			r = sqlite3_step(stmt);
		} while (r == SQLITE_BUSY);

		if (r == SQLITE_ROW) {
			const unsigned char* table = sqlite3_column_text(stmt, 0);
			unsigned long rowid = sqlite3_column_int64(stmt, 1);
			const unsigned char* foreign_table = sqlite3_column_text(stmt, 2);
			unsigned long foreign_rowid = sqlite3_column_int64(stmt, 3);

			// Increment error counter
			errors++;

			// Log the message
			ERROR(db->pakfire, "Foreign key violation found in %s, row %lu: "
				"%lu does not exist in table %s\n", table, rowid, foreign_rowid, foreign_table);

		// Break on anything else
		} else
			break;
	}

	sqlite3_finalize(stmt);

	if (errors)
		ERROR(db->pakfire, "Foreign key check failed\n");
	else
		INFO(db->pakfire, "Foreign key check passed\n");

	return errors;
}

/*
	This function performs an integrity check of the database
*/
PAKFIRE_EXPORT int pakfire_db_check(struct pakfire_db* db) {
	int r;

	// Perform integrity check
	r = pakfire_db_integrity_check(db);
	if (r)
		return 1;

	// Perform foreign key check
	r = pakfire_db_foreign_key_check(db);
	if (r)
		return 1;

	return 0;
}

static int pakfire_db_add_files(struct pakfire_db* db, unsigned long id, PakfireArchive archive) {
	sqlite3_stmt* stmt = NULL;
	int r = 1;

	// Get the filelist from the archive
	PakfireFilelist filelist = pakfire_archive_get_filelist(archive);
	if (!filelist) {
		ERROR(db->pakfire, "Could not fetch filelist from archive\n");
		return 1;
	}

	// Nothing to do if the list is empty
	if (pakfire_filelist_is_empty(filelist))
		goto END;

	const char* sql = "INSERT INTO files(pkg, name, size, type, config, datafile, mode, "
		"user, 'group', hash1, mtime, capabilities) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";

	// Prepare the statement
	r = sqlite3_prepare_v2(db->handle, sql, -1, &stmt, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not prepare SQL statement: %s: %s\n",
			sql, sqlite3_errmsg(db->handle));
		goto END;
	}

	for (unsigned int i = 0; i < pakfire_filelist_size(filelist); i++) {
		PakfireFile file = pakfire_filelist_get(filelist, i);

		// Bind package ID
		r = sqlite3_bind_int64(stmt, 1, id);
		if (r) {
			ERROR(db->pakfire, "Could not bind id: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind name
		const char* name = pakfire_file_get_name(file);

		r = sqlite3_bind_text(stmt, 2, name, -1, NULL);
		if (r) {
			ERROR(db->pakfire, "Could not bind name: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind size
		size_t size = pakfire_file_get_size(file);

		r = sqlite3_bind_int64(stmt, 3, size);
		if (r) {
			ERROR(db->pakfire, "Could not bind size: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind type - XXX this is char which isn't very helpful
		//char type = pakfire_file_get_type(file);

		r = sqlite3_bind_null(stmt, 4);
		if (r) {
			ERROR(db->pakfire, "Could not bind type: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind config - XXX TODO
		r = sqlite3_bind_null(stmt, 5);
		if (r) {
			ERROR(db->pakfire, "Could not bind config: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind datafile - XXX TODO
		r = sqlite3_bind_null(stmt, 6);
		if (r) {
			ERROR(db->pakfire, "Could not bind datafile: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind mode
		mode_t mode = pakfire_file_get_mode(file);

		r = sqlite3_bind_int64(stmt, 7, mode);
		if (r) {
			ERROR(db->pakfire, "Could not bind mode: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind user
		const char* user = pakfire_file_get_user(file);

		r = sqlite3_bind_text(stmt, 8, user, -1, NULL);
		if (r) {
			ERROR(db->pakfire, "Could not bind user: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind group
		const char* group = pakfire_file_get_group(file);

		r = sqlite3_bind_text(stmt, 9, group, -1, NULL);
		if (r) {
			ERROR(db->pakfire, "Could not bind group: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind hash1
		const char* chksum = pakfire_file_get_chksum(file);

		r = sqlite3_bind_text(stmt, 10, chksum, -1, NULL);
		if (r) {
			ERROR(db->pakfire, "Could not bind hash1: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind mtime
		time_t mtime = pakfire_file_get_time(file);

		r = sqlite3_bind_int64(stmt, 11, mtime);
		if (r) {
			ERROR(db->pakfire, "Could not bind mtime: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Bind capabilities - XXX TODO
		r = sqlite3_bind_null(stmt, 12);
		if (r) {
			ERROR(db->pakfire, "Could not bind capabilities: %s\n", sqlite3_errmsg(db->handle));
			pakfire_file_unref(file);
			goto END;
		}

		// Execute query
		do {
			r = sqlite3_step(stmt);
		} while (r == SQLITE_BUSY);

		// Move on to next file
		pakfire_file_unref(file);

		// Reset bound values
		sqlite3_reset(stmt);
	}

	// All okay
	r = 0;

END:
	if (stmt)
		sqlite3_finalize(stmt);

	pakfire_filelist_unref(filelist);

	return r;
}

PAKFIRE_EXPORT int pakfire_db_add_package(struct pakfire_db* db,
		PakfirePackage pkg, PakfireArchive archive) {
	sqlite3_stmt* stmt = NULL;
	int r;

	// Begin a new transaction
	r = pakfire_db_begin_transaction(db);
	if (r)
		goto ROLLBACK;

	const char* sql = "INSERT INTO packages(name, epoch, version, release, arch, groups, "
		"filename, size, inst_size, hash1, license, summary, description, uuid, vendor, "
		"build_host, build_time, installed, repository, reason) VALUES(?, ?, "
		"?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)";

	// Prepare the statement
	r = sqlite3_prepare_v2(db->handle, sql, strlen(sql), &stmt, NULL);
	if (r != SQLITE_OK) {
		ERROR(db->pakfire, "Could not prepare SQL statement: %s: %s\n",
			sql, sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind name
	const char* name = pakfire_package_get_name(pkg);

	r = sqlite3_bind_text(stmt, 1, name, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind name: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind epoch
	unsigned long epoch = pakfire_package_get_epoch(pkg);

	r = sqlite3_bind_int64(stmt, 2, epoch);
	if (r) {
		ERROR(db->pakfire, "Could not bind epoch: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind version
	const char* version = pakfire_package_get_version(pkg);

	r = sqlite3_bind_text(stmt, 3, version, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind version: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind release
	const char* release = pakfire_package_get_release(pkg);

	r = sqlite3_bind_text(stmt, 4, release, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind release: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind arch
	const char* arch = pakfire_package_get_arch(pkg);

	r = sqlite3_bind_text(stmt, 5, arch, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind arch: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind groups
	const char* groups = pakfire_package_get_groups(pkg);

	r = sqlite3_bind_text(stmt, 6, groups, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind groups: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind filename
	const char* filename = pakfire_package_get_filename(pkg);

	r = sqlite3_bind_text(stmt, 7, filename, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind filename: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind size
	unsigned long long size = pakfire_package_get_downloadsize(pkg);

	r = sqlite3_bind_int64(stmt, 8, size);
	if (r) {
		ERROR(db->pakfire, "Could not bind size: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind installed size
	unsigned long long inst_size = pakfire_package_get_installsize(pkg);

	r = sqlite3_bind_int64(stmt, 9, inst_size);
	if (r) {
		ERROR(db->pakfire, "Could not bind inst_size: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind hash1
	const char* hash1 = pakfire_package_get_checksum(pkg);

	r = sqlite3_bind_text(stmt, 10, hash1, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind hash1: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind license
	const char* license = pakfire_package_get_license(pkg);

	r = sqlite3_bind_text(stmt, 11, license, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind license: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind summary
	const char* summary = pakfire_package_get_summary(pkg);

	r = sqlite3_bind_text(stmt, 12, summary, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind summary: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind description
	const char* description = pakfire_package_get_description(pkg);

	r = sqlite3_bind_text(stmt, 13, description, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind description: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind uuid
	const char* uuid = pakfire_package_get_uuid(pkg);

	r = sqlite3_bind_text(stmt, 14, uuid, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind uuid: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind vendor
	const char* vendor = pakfire_package_get_vendor(pkg);

	r = sqlite3_bind_text(stmt, 14, vendor, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind vendor: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind build_host
	const char* buildhost = pakfire_package_get_buildhost(pkg);

	r = sqlite3_bind_text(stmt, 16, buildhost, -1, NULL);
	if (r) {
		ERROR(db->pakfire, "Could not bind build_host: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind build_time
	unsigned long long build_time = pakfire_package_get_buildtime(pkg);

	r = sqlite3_bind_int64(stmt, 17, build_time);
	if (r) {
		ERROR(db->pakfire, "Could not bind build_time: %s\n", sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Bind repository name
	PakfireRepo repo = pakfire_package_get_repo(pkg);
	if (repo) {
		const char* repo_name = pakfire_repo_get_name(repo);
		pakfire_repo_unref(repo);

		r = sqlite3_bind_text(stmt, 18, repo_name, -1, NULL);
		if (r)
			goto ROLLBACK;

	// No repository?
	} else {
		r = sqlite3_bind_null(stmt, 18);
		if (r)
			goto ROLLBACK;
	}

	// XXX TODO Bind reason
	r = sqlite3_bind_null(stmt, 19);
	if (r)
		goto ROLLBACK;

	// Run query
	do {
		r = sqlite3_step(stmt);
	} while (r == SQLITE_BUSY);

	if (r != SQLITE_DONE) {
		ERROR(db->pakfire, "Could not add package to database: %s\n",
			sqlite3_errmsg(db->handle));
		goto ROLLBACK;
	}

	// Save package ID
	unsigned long packages_id = sqlite3_last_insert_rowid(db->handle);

	// This is done
	r = sqlite3_finalize(stmt);
	if (r == SQLITE_OK)
		stmt = NULL;

	// Add files
	r = pakfire_db_add_files(db, packages_id, archive);
	if (r)
		goto ROLLBACK;

	// All done, commit!
	r = pakfire_db_commit(db);
	if (r)
		goto ROLLBACK;

	return 0;

ROLLBACK:
	if (stmt)
		sqlite3_finalize(stmt);

	pakfire_db_rollback(db);

	return 1;
}

PAKFIRE_EXPORT int pakfire_db_remove_package(struct pakfire_db* db, PakfirePackage pkg) {
	return 0; // TODO
}
