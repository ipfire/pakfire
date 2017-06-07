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

#include <assert.h>
#include <solv/transaction.h>

#include <pakfire/i18n.h>
#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/repo.h>
#include <pakfire/step.h>
#include <pakfire/transaction.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PakfireTransaction pakfire_transaction_create(PakfirePool pool, Transaction* trans) {
	PakfireTransaction transaction = pakfire_calloc(1, sizeof(*transaction));
	transaction->pool = pool;

	// Clone the transaction, so we get independent from what ever called this.
	if (trans) {
		transaction->transaction = transaction_create_clone(trans);
		transaction_order(transaction->transaction, 0);
	} else {
		transaction->transaction = transaction_create(trans->pool);
	}

	return transaction;
}

void pakfire_transaction_free(PakfireTransaction transaction) {
	transaction_free(transaction->transaction);
	pakfire_free(transaction);
}

size_t pakfire_transaction_count(PakfireTransaction transaction) {
	return transaction->transaction->steps.count;
}

ssize_t pakfire_transaction_installsizechange(PakfireTransaction transaction) {
	ssize_t sizechange = transaction_calc_installsizechange(transaction->transaction);

	// Convert from kbytes to bytes
	return sizechange * 1024;
}

ssize_t pakfire_transaction_downloadsize(PakfireTransaction transaction) {
	PakfirePool pool = pakfire_transaction_pool(transaction);
	ssize_t size = 0;

	for (int i = 0; i < transaction->transaction->steps.count; i++) {
		Id p = transaction->transaction->steps.elements[i];
		Id t = transaction_type(transaction->transaction, p,
			SOLVER_TRANSACTION_SHOW_OBSOLETES |
			SOLVER_TRANSACTION_CHANGE_IS_REINSTALL |
			SOLVER_TRANSACTION_SHOW_ALL |
			SOLVER_TRANSACTION_SHOW_ACTIVE);

		// Erasing a package does not require us to download it
		if (t == SOLVER_TRANSACTION_ERASE)
			continue;

		// Get the package for this step
		PakfirePackage pkg = pakfire_package_create(pool, p);

		if (!pakfire_package_is_cached(pkg))
			size += pakfire_package_get_downloadsize(pkg);

		pakfire_package_free(pkg);
	}

	return size;
}

PakfireStep pakfire_transaction_get_step(PakfireTransaction transaction, int index) {
	Transaction* trans = transaction->transaction;

	if (index >= trans->steps.count)
		return NULL;

	return pakfire_step_create(transaction, trans->steps.elements[index]);
}

PakfirePackageList pakfire_transaction_get_packages(PakfireTransaction transaction, int type) {
	PakfirePool pool = pakfire_transaction_pool(transaction);

	PakfirePackageList packagelist = pakfire_packagelist_create();

	for (int i = 0; i < transaction->transaction->steps.count; i++) {
		Id p = transaction->transaction->steps.elements[i];
		Id t = transaction_type(transaction->transaction, p,
			SOLVER_TRANSACTION_SHOW_OBSOLETES |
			SOLVER_TRANSACTION_CHANGE_IS_REINSTALL |
			SOLVER_TRANSACTION_SHOW_ALL |
			SOLVER_TRANSACTION_SHOW_ACTIVE);

		if (t == type) {
			PakfirePackage package = pakfire_package_create(pool, p);
			pakfire_packagelist_push(packagelist, package);
		}
	}

	// Sort list in place
	pakfire_packagelist_sort(packagelist);

	return packagelist;
}

static void pakfire_transaction_add_headline(char** str, size_t width, const char* headline) {
	assert(headline);

	asprintf(str, "%s%s\n", *str, headline);
}

static void pakfire_transaction_add_newline(char** str, size_t width) {
	asprintf(str, "%s\n", *str);
}

static void pakfire_transaction_add_line(char** str, size_t width, const char* name,
		const char* arch, const char* version, const char* repo, const char* size) {
	// XXX need to adapt to size
	asprintf(str, "%s %-21s %-8s %-21s %-18s %6s \n", *str, name, arch, version, repo, size);
}

static void pakfire_transaction_add_package(char** str, size_t width, PakfirePackage pkg) {
	PakfireRepo repo = pakfire_package_get_repo(pkg);

	unsigned long long size = pakfire_package_get_size(pkg);
	char* size_str = pakfire_format_size(size);

	pakfire_transaction_add_line(str, width,
		pakfire_package_get_name(pkg),
		pakfire_package_get_arch(pkg),
		pakfire_package_get_evr(pkg),
		pakfire_repo_get_name(repo),
		size_str
	);

	pakfire_repo_free(repo);
	pakfire_free(size_str);
}

static void pakfire_transaction_add_separator(char** str, size_t width) {
	while (width-- > 0)
		asprintf(str, "%s=", *str);

	// newline
	asprintf(str, "%s\n", *str);
}

static size_t pakfire_transaction_add_section(char** str, size_t width, PakfireTransaction transaction,
		const char* headline, int type) {
	PakfirePackageList list = pakfire_transaction_get_packages(transaction, type);

	// Nothing to do if there are no packages in this stage
	size_t c = pakfire_packagelist_count(list);
	if (c == 0)
		goto END;

	// Headline
	pakfire_transaction_add_headline(str, width, headline);

	// List each package
	for (unsigned int i = 0; i < c; i++) {
		PakfirePackage pkg = pakfire_packagelist_get(list, i);
		pakfire_transaction_add_package(str, width, pkg);
	}

	// newline
	pakfire_transaction_add_newline(str, width);

END:
	pakfire_packagelist_free(list);

	return c;
}

static void pakfire_transaction_add_summary_line(char** str, size_t width, const char* headline, size_t pkgs) {
	if (pkgs > 0)
		asprintf(str, "%s%-20s %-4zu %s\n", *str, headline, pkgs, _("package(s)"));
}

static void pakfire_transaction_add_usage_line(char** str, size_t width, const char* headline, ssize_t size) {
	char* s = pakfire_format_size(size);

	asprintf(str, "%s%-21s: %s\n", *str, headline, s);

	pakfire_free(s);
}

char* pakfire_transaction_dump(PakfireTransaction transaction, size_t width) {
	char* string = "";

	// Header
	pakfire_transaction_add_separator(&string, width);
	pakfire_transaction_add_line(&string, width,
		_("Package"),
		_("Arch"),
		_("Version"),
		_("Repository"),
		_("Size")
	);
	pakfire_transaction_add_separator(&string, width);

	// Show what we are doing
	size_t installing = pakfire_transaction_add_section(&string, width, transaction,
		_("Installing:"), SOLVER_TRANSACTION_INSTALL);
	size_t reinstalling = pakfire_transaction_add_section(&string, width, transaction,
		_("Reinstalling:"), SOLVER_TRANSACTION_REINSTALL);
	size_t updating = pakfire_transaction_add_section(&string, width, transaction,
		_("Updating:"), SOLVER_TRANSACTION_UPGRADE);
	size_t downgrading = pakfire_transaction_add_section(&string, width, transaction,
		_("Downgrading:"), SOLVER_TRANSACTION_DOWNGRADE);
	size_t removing = pakfire_transaction_add_section(&string, width, transaction,
		_("Removing:"), SOLVER_TRANSACTION_ERASE);
	size_t obsoleting = pakfire_transaction_add_section(&string, width, transaction,
		_("Obsoleting:"), SOLVER_TRANSACTION_OBSOLETES);

	// Summary
	pakfire_transaction_add_headline(&string, width, _("Transaction Summary"));
	pakfire_transaction_add_separator(&string, width);

	pakfire_transaction_add_summary_line(&string, width, _("Installing:"), installing);
	pakfire_transaction_add_summary_line(&string, width, _("Reinstalling:"), reinstalling);
	pakfire_transaction_add_summary_line(&string, width, _("Updating:"), updating);
	pakfire_transaction_add_summary_line(&string, width, _("Downgrading:"), downgrading);
	pakfire_transaction_add_summary_line(&string, width, _("Removing:"), removing);
	pakfire_transaction_add_summary_line(&string, width, _("Obsoleting:"), obsoleting);

	// How much do we need to download?
	size_t downloadsize = pakfire_transaction_downloadsize(transaction);
	if (downloadsize > 0)
		pakfire_transaction_add_usage_line(&string, width,
			_("Total Download Size"), downloadsize);

	// How much more space do we need?
	ssize_t sizechange = pakfire_transaction_installsizechange(transaction);

	pakfire_transaction_add_usage_line(&string, width,
		(sizechange >= 0) ? _("Installed Size") : _("Freed Size"), sizechange);

	// Remove trailing newline
	size_t l = strlen(string) - 1;

	if (l > 0 && string[l] == '\n')
		string[l] = '\0';

	return string;
}
