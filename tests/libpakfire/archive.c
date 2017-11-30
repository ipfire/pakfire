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

#include <pakfire/archive.h>
#include <pakfire/util.h>

#include "../testsuite.h"

static const char* TEST_PKG1_PATH = "data/beep-1.3-2.ip3.x86_64.pfm";

int test_open(const test_t* t) {
    char* path = pakfire_path_join(TEST_SRC_PATH, TEST_PKG1_PATH);
    LOG("Trying to open %s\n", path);

    // Open the archive
    PakfireArchive archive = pakfire_archive_open(t->pakfire, path);
    assert_return(archive, EXIT_FAILURE);

    pakfire_archive_unref(archive);

    pakfire_free(path);

    return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_init();

	testsuite_t* ts = testsuite_create(1);

	testsuite_add_test(ts, "test_open", test_open);

	return testsuite_run(ts);
}
