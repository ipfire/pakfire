/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2019 Pakfire development team                                 #
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

#include <pakfire/execute.h>
#include <pakfire/util.h>

#include "../testsuite.h"

int test_does_not_exist(const test_t* t) {
	const char* cmd = "/usr/bin/does-not-exist";

	int r = pakfire_execute(t->pakfire, cmd, NULL, 0);
	assert_return(r != 0, EXIT_FAILURE);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_init();

	testsuite_t* ts = testsuite_create(1);

	testsuite_add_test(ts, "test_does_not_exist", test_does_not_exist);

	return testsuite_run(ts);
}
