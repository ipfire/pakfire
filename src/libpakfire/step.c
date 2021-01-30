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

#include <errno.h>
#include <stdbool.h>
#include <stdlib.h>
#include <unistd.h>

#include <pakfire/archive.h>
#include <pakfire/constants.h>
#include <pakfire/db.h>
#include <pakfire/execute.h>
#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/pakfire.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/scriptlet.h>
#include <pakfire/step.h>
#include <pakfire/transaction.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define LDCONFIG "/sbin/ldconfig"

struct _PakfireStep {
	Pakfire pakfire;
	PakfirePackage package;
	PakfireArchive archive;
	pakfire_step_type_t type;
	int nrefs;
};

PAKFIRE_EXPORT PakfireStep pakfire_step_create(PakfireTransaction transaction,
		pakfire_step_type_t type, PakfirePackage pkg) {
	Pakfire pakfire = pakfire_transaction_get_pakfire(transaction);

	PakfireStep step = pakfire_calloc(1, sizeof(*step));
	if (step) {
		DEBUG(pakfire, "Allocated Step at %p\n", step);
		step->pakfire = pakfire_ref(pakfire);
		step->nrefs = 1;

		// Save everything
		step->type = type;
		step->package = pakfire_package_ref(pkg);
	}

	pakfire_unref(pakfire);

	return step;
}

PAKFIRE_EXPORT PakfireStep pakfire_step_ref(PakfireStep step) {
	step->nrefs++;

	return step;
}

static void pakfire_step_free(PakfireStep step) {
	DEBUG(step->pakfire, "Releasing Step at %p\n", step);

	pakfire_package_unref(step->package);
	pakfire_archive_unref(step->archive);
	pakfire_unref(step->pakfire);
	pakfire_free(step);
}

PAKFIRE_EXPORT PakfireStep pakfire_step_unref(PakfireStep step) {
	if (!step)
		return NULL;

	if (--step->nrefs > 0)
		return step;

	pakfire_step_free(step);
	return NULL;
}

PAKFIRE_EXPORT PakfirePackage pakfire_step_get_package(PakfireStep step) {
	return pakfire_package_ref(step->package);
}

PAKFIRE_EXPORT pakfire_step_type_t pakfire_step_get_type(PakfireStep step) {
	return step->type;
}

PAKFIRE_EXPORT const char* pakfire_step_get_type_string(PakfireStep step) {
	pakfire_step_type_t type = pakfire_step_get_type(step);

	switch(type) {
		case PAKFIRE_STEP_INSTALL:
			return "install";

		case PAKFIRE_STEP_REINSTALL:
			return "reinstall";

		case PAKFIRE_STEP_ERASE:
			return "erase";

		case PAKFIRE_STEP_DOWNGRADE:
			return "downgrade";

		case PAKFIRE_STEP_UPGRADE:
			return "upgrade";

		case PAKFIRE_STEP_OBSOLETE:
			return "obsolete";

		case PAKFIRE_STEP_IGNORE:
		default:
			return NULL;
	}
}

static int pakfire_step_get_downloadtype(PakfireStep step) {
	int type = pakfire_step_get_type(step);

	switch (type) {
		case PAKFIRE_STEP_INSTALL:
		case PAKFIRE_STEP_REINSTALL:
		case PAKFIRE_STEP_DOWNGRADE:
		case PAKFIRE_STEP_UPGRADE:
			return 1;

		default:
			break;
	}

	return 0;
}

PAKFIRE_EXPORT size_t pakfire_step_get_downloadsize(PakfireStep step) {
	if (pakfire_step_get_downloadtype(step))
		return pakfire_package_get_downloadsize(step->package);

	return 0;
}

PAKFIRE_EXPORT ssize_t pakfire_step_get_installsizechange(PakfireStep step) {
	ssize_t installsize = pakfire_package_get_installsize(step->package);

	pakfire_step_type_t type = pakfire_step_get_type(step);
	switch (type) {
		case PAKFIRE_STEP_IGNORE:
		case PAKFIRE_STEP_ERASE:
		case PAKFIRE_STEP_OBSOLETE:
			installsize *= -1;
			break;

		default:
			break;
	}

	return installsize;
}

PAKFIRE_EXPORT int pakfire_step_needs_download(PakfireStep step) {
	if (!pakfire_step_get_downloadtype(step))
		return false;

	PakfireRepo repo = pakfire_package_get_repo(step->package);
	if (pakfire_repo_is_installed_repo(repo) == 0)
		return false;

	// Return false if package is in cache.
	if (pakfire_package_is_cached(step->package))
		return false;

	return true;
}

static int pakfire_step_verify(PakfireStep step) {
	// The package must have been downloaded
	if (pakfire_step_needs_download(step))
		return 1;

	// Fetch the archive
	step->archive = pakfire_package_get_archive(step->package);
	if (!step->archive) {
		char* nevra = pakfire_package_get_nevra(step->package);
		char* cache_path = pakfire_package_get_cache_path(step->package);

		ERROR(step->pakfire, "Could not open package archive for %s: %s\n",
			nevra, cache_path);

		pakfire_free(nevra);
		pakfire_free(cache_path);

		return -1;
	}

	// Verify the archive
	pakfire_archive_verify_status_t status = pakfire_archive_verify(step->archive);

	// Log error
	if (status) {
		const char* error = pakfire_archive_verify_strerror(status);
		ERROR(step->pakfire, "Archive verification failed: %s\n", error);
	}

	return status;
}

static int pakfire_script_check_shell(struct pakfire_scriptlet* scriptlet) {
	const char* interpreter = "#!/bin/sh";

	// data must be long enough
	if (scriptlet->size <= strlen(interpreter))
		return 0;

	// If the string begins with the interpreter, this is a match
	if (strncmp(scriptlet->data, interpreter, strlen(interpreter)) == 0)
		return 1;

	return 0;
}

static int pakfire_step_run_shell_script(PakfireStep step, struct pakfire_scriptlet* scriptlet) {
	const char* root = pakfire_get_path(step->pakfire);

	// Write the scriptlet to disk
	char* path = pakfire_path_join(root, "tmp/.pakfire-scriptlet.XXXXXX");
	int r;

	DEBUG(step->pakfire, "Writing script to %s\n", path);

	// Open a temporary file
	int fd = mkstemp(path);
	if (fd < 0) {
		ERROR(step->pakfire, "Could not open a temporary file: %s\n",
			strerror(errno));

		r = errno;
	}

	// Write data
	ssize_t bytes_written = write(fd, scriptlet->data, scriptlet->size);
	if (bytes_written < (ssize_t)scriptlet->size) {
		ERROR(step->pakfire, "Could not write script to file %s: %s\n",
			path, strerror(errno));

		r = errno;
		goto out;
	}

	// Make the script executable
	r = fchmod(fd, S_IRUSR|S_IWUSR|S_IXUSR);
	if (r) {
		ERROR(step->pakfire, "Could not set executable permissions on %s: %s\n",
			path, strerror(errno));

		r = errno;
		goto out;
	}

	// Close file
	r = close(fd);
	if (r) {
		ERROR(step->pakfire, "Could not close script file %s: %s\n",
			path, strerror(errno));

		r = errno;
		goto out;
	}

	const char* command = path;
	if (root)
		command = pakfire_path_relpath(root, path);

	// Run the script
	r = pakfire_execute_command(step->pakfire, command, NULL, 0, NULL);
	if (r) {
		DEBUG(step->pakfire, "Script return code: %d\n", r);
	}

out:
	// Remove script from disk
	unlink(path);

	// Cleanup
	pakfire_free(path);

	return r;
}

static int pakfire_step_run_script(PakfireStep step, pakfire_scriptlet_type type) {
	// Fetch scriptlet from archive
	struct pakfire_scriptlet* scriptlet = pakfire_archive_get_scriptlet(step->archive, type);
	if (!scriptlet)
		return 0;

	// Found a script!
	DEBUG(step->pakfire, "Found scriptlet:\n%.*s",
		(int)scriptlet->size, (const char*)scriptlet->data);

	// Detect what kind of script this is and run it
	if (pakfire_script_check_shell(scriptlet)) {
		pakfire_step_run_shell_script(step, scriptlet);
	} else {
		ERROR(step->pakfire, "Scriptlet is of an unknown kind\n");
	}

	return 0;
}

static int pakfire_run_ldconfig(PakfireStep step) {
	int r = -1;

	// XXX check if package has some files that require to run ldconfig

	const char* path = pakfire_get_path(step->pakfire);

	if (pakfire_access(step->pakfire, path, LDCONFIG, X_OK) == 0) {
		r = pakfire_execute_command(step->pakfire, LDCONFIG, NULL, 0, NULL);

		DEBUG(step->pakfire, "ldconfig returned %d\n", r);
	}

	return r;
}

static int pakfire_step_extract(PakfireStep step) {
	if (!step->archive) {
		ERROR(step->pakfire, "Archive was not opened\n");
		return -1;
	}

	// Extract payload to the root of the Pakfire instance
	int r = pakfire_archive_extract(step->archive, NULL, PAKFIRE_ARCHIVE_USE_PAYLOAD);
	if (r) {
		char* nevra = pakfire_package_get_nevra(step->package);
		ERROR(step->pakfire, "Could not extract package %s: %d\n", nevra, r);
		pakfire_free(nevra);
	}

	// Update the runtime linker cache
	pakfire_run_ldconfig(step);

	return r;
}

static int pakfire_step_erase(PakfireStep step) {
	// Update the runtime linker cache after all files have been removed
	pakfire_run_ldconfig(step);

	return 0; // TODO
}

PAKFIRE_EXPORT int pakfire_step_run(PakfireStep step,
		struct pakfire_db* db, const pakfire_action_type_t action) {
	DEBUG(step->pakfire, "Running Step %p (%s)\n", step, pakfire_action_type_string(action));

	pakfire_step_type_t type = pakfire_step_get_type(step);

	int r = 0;
	switch (action) {
		// Verify this step
		case PAKFIRE_ACTION_VERIFY:
			r = pakfire_step_verify(step);
			break;

		// Run the pre-transaction scripts
		case PAKFIRE_ACTION_PRETRANS:
			switch (type) {
				case PAKFIRE_STEP_INSTALL:
				case PAKFIRE_STEP_REINSTALL:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_PRETRANSIN);
					break;

				case PAKFIRE_STEP_UPGRADE:
				case PAKFIRE_STEP_DOWNGRADE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_PRETRANSUP);
					break;

				case PAKFIRE_STEP_ERASE:
				case PAKFIRE_STEP_OBSOLETE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_PRETRANSUN);
					break;

				case PAKFIRE_STEP_IGNORE:
					break;
			}
			break;

		// Run the post-transaction scripts
		case PAKFIRE_ACTION_POSTTRANS:
			switch (type) {
				case PAKFIRE_STEP_INSTALL:
				case PAKFIRE_STEP_REINSTALL:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_POSTTRANSIN);
					break;

				case PAKFIRE_STEP_UPGRADE:
				case PAKFIRE_STEP_DOWNGRADE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_POSTTRANSUP);
					break;

				case PAKFIRE_STEP_ERASE:
				case PAKFIRE_STEP_OBSOLETE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_POSTTRANSUN);
					break;

				case PAKFIRE_STEP_IGNORE:
					break;
			}
			break;

		// Execute the action of this script
		case PAKFIRE_ACTION_EXECUTE:
			switch (type) {
				case PAKFIRE_STEP_INSTALL:
				case PAKFIRE_STEP_REINSTALL:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_PREIN);
					if (r)
						break;

					r = pakfire_step_extract(step);
					if (r)
						break;

					r = pakfire_db_add_package(db, step->package, step->archive);
					if (r)
						break;

					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_POSTIN);
					break;

				case PAKFIRE_STEP_UPGRADE:
				case PAKFIRE_STEP_DOWNGRADE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_PREUP);
					if (r)
						break;

					r = pakfire_step_extract(step);
					if (r)
						break;

					r = pakfire_db_add_package(db, step->package, step->archive);
					if (r)
						break;

					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_POSTUP);
					break;

				case PAKFIRE_STEP_ERASE:
				case PAKFIRE_STEP_OBSOLETE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_PREUN);
					if (r)
						break;

					r = pakfire_step_erase(step);
					if (r)
						break;

					r = pakfire_db_remove_package(db, step->package);
					if (r)
						break;

					r = pakfire_step_run_script(step, PAKFIRE_SCRIPTLET_POSTUN);
					break;

				case PAKFIRE_STEP_IGNORE:
					break;
			}
			break;

		// Do nothing
		case PAKFIRE_ACTION_NOOP:
			break;
	}

	if (r)
		ERROR(step->pakfire, "Step has failed: %s\n", strerror(r));

	return r;
}
