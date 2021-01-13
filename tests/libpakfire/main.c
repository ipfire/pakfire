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

#include <string.h>

#include <pakfire/pakfire.h>

#include "../testsuite.h"

static int test_init(const test_t* t) {
	LOG("Allocated at %p\n", t->pakfire);

	return EXIT_SUCCESS;
}

static int test_path(const test_t* t) {
	const char* path = pakfire_get_path(t->pakfire);
	assert_return(strcmp(path, TEST_ROOTFS) == 0, EXIT_FAILURE);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_t* ts = testsuite_create(2);

	testsuite_add_test(ts, test_init);
	testsuite_add_test(ts, test_path);

	return testsuite_run(ts);
}
