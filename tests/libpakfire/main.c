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

#include <pakfire/pakfire.h>

#include "../testsuite.h"

static int test_init(const test_t* t) {
	Pakfire pakfire = pakfire_create("/", "x86_64");
	if (!pakfire)
		return EXIT_FAILURE;

	LOG("Allocated at %p\n", pakfire);

	pakfire_unref(pakfire);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_t* ts = testsuite_create(1);

	testsuite_add_test(ts, "test_init", test_init);

	return testsuite_run(ts);
}
