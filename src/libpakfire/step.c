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
#include <pakfire/package.h>
#include <pakfire/repo.h>
#include <pakfire/step.h>
#include <pakfire/transaction.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PakfireStep pakfire_step_create(PakfireTransaction transaction, Id id) {
	PakfireStep step = pakfire_calloc(1, sizeof(*step));

	step->pool = pakfire_transaction_pool(transaction);
	step->transaction = transaction;
	step->id = id;

	return step;
}

void pakfire_step_free(PakfireStep step) {
	pakfire_free(step);
}

PakfirePackage pakfire_step_get_package(PakfireStep step) {
	return pakfire_package_create(step->pool, step->id);
}

pakfire_step_type pakfire_step_get_type(PakfireStep step) {
	Transaction* trans = step->transaction->transaction;

	int type = transaction_type(trans, step->id,
		SOLVER_TRANSACTION_SHOW_ACTIVE|SOLVER_TRANSACTION_CHANGE_IS_REINSTALL);

	// Translate solver types into our own types
	switch (type) {
		case SOLVER_TRANSACTION_INSTALL:
		case SOLVER_TRANSACTION_MULTIINSTALL:
		case SOLVER_TRANSACTION_REINSTALL:
		case SOLVER_TRANSACTION_MULTIREINSTALL:
			return PAKFIRE_STEP_INSTALL;

		case SOLVER_TRANSACTION_ERASE:
			return PAKFIRE_STEP_ERASE;

		case SOLVER_TRANSACTION_DOWNGRADE:
			return PAKFIRE_STEP_DOWNGRADE;

		case SOLVER_TRANSACTION_UPGRADE:
			return PAKFIRE_STEP_UPGRADE;

		// Anything we don't care about
		case SOLVER_TRANSACTION_IGNORE:
		case SOLVER_TRANSACTION_REINSTALLED:
		case SOLVER_TRANSACTION_DOWNGRADED:
		default:
				return PAKFIRE_STEP_IGNORE;
	}
}

const char* pakfire_step_get_type_string(PakfireStep step) {
	pakfire_step_type type = pakfire_step_get_type(step);

	switch(type) {
		case PAKFIRE_STEP_INSTALL:
			return "install";

		case PAKFIRE_STEP_ERASE:
			return "erase";

		case PAKFIRE_STEP_DOWNGRADE:
			return "downgrade";

		case PAKFIRE_STEP_UPGRADE:
			return "upgrade";

		case PAKFIRE_STEP_IGNORE:
		default:
			return NULL;
	}
}

static int pakfire_step_get_downloadtype(PakfireStep step) {
	int type = pakfire_step_get_type(step);

	switch (type) {
		case PAKFIRE_STEP_INSTALL:
		case PAKFIRE_STEP_DOWNGRADE:
		case PAKFIRE_STEP_UPGRADE:
			return 1;

		default:
			break;
	}

	return 0;
}

unsigned long long pakfire_step_get_downloadsize(PakfireStep step) {
	PakfirePackage pkg = NULL;
	int downloadsize = 0;

	if (pakfire_step_get_downloadtype(step)) {
		pkg = pakfire_step_get_package(step);
		downloadsize = pakfire_package_get_downloadsize(pkg);
	}

	if (pkg)
		pakfire_package_free(pkg);

	return downloadsize;
}

long pakfire_step_get_installsizechange(PakfireStep step) {
	PakfirePackage pkg = pakfire_step_get_package(step);
	int installsize = pakfire_package_get_installsize(pkg);

	int type = pakfire_step_get_type(step);
	switch (type) {
		case SOLVER_TRANSACTION_IGNORE:
		case SOLVER_TRANSACTION_ERASE:
			installsize *= -1;
			break;
	}

	pakfire_package_free(pkg);

	return installsize;
}

int pakfire_step_needs_download(PakfireStep step) {
	PakfirePackage pkg = NULL;
	int ret = true;

	if (!pakfire_step_get_downloadtype(step))
		return false;

	/* Get the package object. */
	pkg = pakfire_step_get_package(step);

	PakfireRepo repo = pakfire_package_get_repo(pkg);
	if (pakfire_repo_is_installed_repo(repo)) {
		ret = false;
		goto finish;
	}

	PakfireCache cache = pakfire_pool_get_cache(step->pool);
	if (!cache)
		goto finish;

	// Return false if package is in cache.
	ret = !pakfire_cache_has_package(cache, pkg);

finish:
	if (pkg)
		pakfire_package_free(pkg);

	return ret;
}
