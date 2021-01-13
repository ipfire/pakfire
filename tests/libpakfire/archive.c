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

#include <unistd.h>

#include <pakfire/archive.h>
#include <pakfire/package.h>
#include <pakfire/repo.h>
#include <pakfire/util.h>

#include "../testsuite.h"

static const char* TEST_PKG1_PATH = "data/beep-1.3-2.ip3.x86_64.pfm";
static const char* TEST_PKG1_FILE = "usr/bin/beep";

static int test_open(const struct test* t) {
	char* path = pakfire_path_join(TEST_SRC_PATH, TEST_PKG1_PATH);
	LOG("Trying to open %s\n", path);

	// Open the archive
	PakfireArchive archive = pakfire_archive_open(t->pakfire, path);
	ASSERT(archive);

	// Verify the archive
	pakfire_archive_verify_status_t verify = pakfire_archive_verify(archive);
	ASSERT(verify == PAKFIRE_ARCHIVE_VERIFY_OK);

	pakfire_archive_unref(archive);
	pakfire_free(path);

	return EXIT_SUCCESS;
}

static int test_extract(const struct test* t) {
	char* path = pakfire_path_join(TEST_SRC_PATH, TEST_PKG1_PATH);

	PakfireArchive archive = pakfire_archive_open(t->pakfire, path);
	pakfire_free(path);

	// Extract the archive payload
	int r = pakfire_archive_extract(archive, NULL, PAKFIRE_ARCHIVE_USE_PAYLOAD);
	ASSERT(r == 0);

	// Check if test file from the archive exists
	ASSERT(pakfire_access(t->pakfire, pakfire_get_path(t->pakfire),
		TEST_PKG1_FILE, F_OK) == 0);

	pakfire_archive_unref(archive);

	return EXIT_SUCCESS;
}

static int test_import(const struct test* t) {
	char* path = pakfire_path_join(TEST_SRC_PATH, TEST_PKG1_PATH);

	PakfireArchive archive = pakfire_archive_open(t->pakfire, path);
	pakfire_free(path);

	PakfireRepo repo = pakfire_repo_create(t->pakfire, "tmp");
	ASSERT(repo);

	PakfirePackage pkg = pakfire_repo_add_archive(repo, archive);
	ASSERT(pkg);

	pakfire_repo_unref(repo);
	pakfire_package_unref(pkg);
	pakfire_archive_unref(archive);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_add_test(test_open);
	testsuite_add_test(test_extract);
	testsuite_add_test(test_import);

	return testsuite_run();
}
