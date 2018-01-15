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

#include <stdbool.h>

#include <solv/pooltypes.h>
#include <solv/transaction.h>

#include <pakfire/cache.h>
#include <pakfire/constants.h>
#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/pool.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/step.h>
#include <pakfire/transaction.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

struct _PakfireStep {
	PakfirePool pool;
	PakfirePackage package;
	pakfire_step_type_t type;
	int nrefs;
};

static pakfire_step_type_t get_type(Transaction* transaction, Id id) {
	int type = transaction_type(transaction, id,
		SOLVER_TRANSACTION_SHOW_ACTIVE|SOLVER_TRANSACTION_CHANGE_IS_REINSTALL);

	// Translate solver types into our own types
	switch (type) {
		case SOLVER_TRANSACTION_INSTALL:
		case SOLVER_TRANSACTION_MULTIINSTALL:
			return PAKFIRE_STEP_INSTALL;

		case SOLVER_TRANSACTION_REINSTALL:
		case SOLVER_TRANSACTION_MULTIREINSTALL:
			return PAKFIRE_STEP_REINSTALL;

		case SOLVER_TRANSACTION_ERASE:
			return PAKFIRE_STEP_ERASE;

		case SOLVER_TRANSACTION_DOWNGRADE:
			return PAKFIRE_STEP_DOWNGRADE;

		case SOLVER_TRANSACTION_UPGRADE:
			return PAKFIRE_STEP_UPGRADE;

		case SOLVER_TRANSACTION_OBSOLETES:
			return PAKFIRE_STEP_OBSOLETE;

		// Anything we don't care about
		case SOLVER_TRANSACTION_IGNORE:
		case SOLVER_TRANSACTION_REINSTALLED:
		case SOLVER_TRANSACTION_DOWNGRADED:
		default:
				return PAKFIRE_STEP_IGNORE;
	}
}

PAKFIRE_EXPORT PakfireStep pakfire_step_create(PakfireTransaction transaction, Id id) {
	Transaction* t = pakfire_transaction_get_transaction(transaction);

	PakfireStep step = pakfire_calloc(1, sizeof(*step));
	if (step) {
		DEBUG("Allocated Step at %p\n", step);
		step->nrefs = 1;

		step->pool = pakfire_transaction_get_pool(transaction);
		step->type = get_type(t, id);

		// Get the package
		step->package = pakfire_package_create(step->pool, id);
	}

	return step;
}

PAKFIRE_EXPORT PakfireStep pakfire_step_ref(PakfireStep step) {
	step->nrefs++;

	return step;
}

static void pakfire_step_free(PakfireStep step) {
	pakfire_package_unref(step->package);
	pakfire_pool_unref(step->pool);
	pakfire_free(step);

	DEBUG("Released Step at %p\n", step);
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
	int ret = true;

	if (!pakfire_step_get_downloadtype(step))
		return false;

	PakfireRepo repo = pakfire_package_get_repo(step->package);
	if (pakfire_repo_is_installed_repo(repo)) {
		ret = false;
		goto finish;
	}

	PakfireCache cache = pakfire_pool_get_cache(step->pool);
	if (!cache)
		goto finish;

	// Return false if package is in cache.
	ret = !pakfire_cache_has_package(cache, step->package);

finish:
	return ret;
}

static int pakfire_step_verify(PakfireStep step) {
	// The package must have been downloaded
	if (pakfire_step_needs_download(step))
		return 1;

	// TODO verify package and signature

	return 0;
}

static int pakfire_step_run_script(PakfireStep step, pakfire_script_type script) {
	return 0; // XXX
}

static int pakfire_step_extract(PakfireStep step) {
	return 0; // TODO
}

static int pakfire_step_erase(PakfireStep step) {
	return 0; // TODO
}

PAKFIRE_EXPORT int pakfire_step_run(PakfireStep step, const pakfire_action_type action) {
	pakfire_step_type_t type = pakfire_step_get_type(step);

	int r = 0;
	switch (action) {
		// Verify this step
		case PAKFIRE_ACTION_VERIFY:
			r = pakfire_step_verify(step);
			goto END;

		// Run the pre-transaction scripts
		case PAKFIRE_ACTION_PRETRANS:
			switch (type) {
				case PAKFIRE_STEP_INSTALL:
				case PAKFIRE_STEP_REINSTALL:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_PRETRANSIN);
					break;

				case PAKFIRE_STEP_UPGRADE:
				case PAKFIRE_STEP_DOWNGRADE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_PRETRANSUP);
					break;

				case PAKFIRE_STEP_ERASE:
				case PAKFIRE_STEP_OBSOLETE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_PRETRANSUN);
					break;

				case PAKFIRE_STEP_IGNORE:
					break;
			}
			goto END;

		// Run the post-transaction scripts
		case PAKFIRE_ACTION_POSTTRANS:
			switch (type) {
				case PAKFIRE_STEP_INSTALL:
				case PAKFIRE_STEP_REINSTALL:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_POSTTRANSIN);
					break;

				case PAKFIRE_STEP_UPGRADE:
				case PAKFIRE_STEP_DOWNGRADE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_POSTTRANSUP);
					break;

				case PAKFIRE_STEP_ERASE:
				case PAKFIRE_STEP_OBSOLETE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_POSTTRANSUN);
					break;

				case PAKFIRE_STEP_IGNORE:
					break;
			}
			goto END;

		// Execute the action of this script
		case PAKFIRE_ACTION_EXECUTE:
			switch (type) {
				case PAKFIRE_STEP_INSTALL:
				case PAKFIRE_STEP_REINSTALL:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_PREIN);
					if (r)
						goto END;

					r = pakfire_step_extract(step);
					if (r)
						goto END;

					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_POSTIN);
					break;

				case PAKFIRE_STEP_UPGRADE:
				case PAKFIRE_STEP_DOWNGRADE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_PREUP);
					if (r)
						goto END;

					r = pakfire_step_extract(step);
					if (r)
						goto END;

					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_POSTUP);
					break;

				case PAKFIRE_STEP_ERASE:
				case PAKFIRE_STEP_OBSOLETE:
					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_PREUN);
					if (r)
						goto END;

					r = pakfire_step_erase(step);
					if (r)
						goto END;

					r = pakfire_step_run_script(step, PAKFIRE_SCRIPT_POSTUN);
					break;

				case PAKFIRE_STEP_IGNORE:
					break;
			}
			goto END;

		// Do nothing
		case PAKFIRE_ACTION_NOOP:
			goto END;
	}

END:
	return r;
}
