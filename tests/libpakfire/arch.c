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

#include <pakfire/arch.h>
#include <pakfire/util.h>

#include "../testsuite.h"

static int test_native(const struct test* t) {
	// First call
	const char* arch1 = pakfire_arch_native();
	ASSERT(arch1);

	// Second call
	const char* arch2 = pakfire_arch_native();
	ASSERT(arch2);

	// Must be the same pointer
	ASSERT(arch1 == arch2);

	return EXIT_SUCCESS;
}

static int test_supported(const struct test* t) {
	int r;

	r = pakfire_arch_supported("x86_64");
	ASSERT(r);

	r = pakfire_arch_supported("i686");
	ASSERT(r);

	// Check non-existant architecture
	r = pakfire_arch_supported("ABC");
	ASSERT(!r);

	return EXIT_SUCCESS;
}

static int test_compatible(const struct test* t) {
	int r;

	// x86_64 can build i686
	r = pakfire_arch_is_compatible("x86_64", "i686");
	ASSERT(r);

	// i686 can NOT build i686
	r = pakfire_arch_is_compatible("i686", "x86_64");
	ASSERT(!r);

	// x86_64 can build itself
	r = pakfire_arch_is_compatible("x86_64", "x86_64");
	ASSERT(r);

	// x86_64 can NOT build a non-existant architecture
	r = pakfire_arch_is_compatible("x86_64", "ABC");
	ASSERT(!r);

	// A non-existant architecture cannot build anything
	r = pakfire_arch_is_compatible("ABC", "x86_64");
	ASSERT(!r);

	return EXIT_SUCCESS;
}

static int test_machine(const struct test* t) {
	char* machine;

	machine = pakfire_arch_machine("x86_64", "ipfire");
	ASSERT_STRING_EQUALS(machine, "x86_64-ipfire-linux-gnu");

	machine = pakfire_arch_machine("x86_64", "IPFIRE");
	ASSERT_STRING_EQUALS(machine, "x86_64-ipfire-linux-gnu");

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_add_test(test_native);
	testsuite_add_test(test_supported);
	testsuite_add_test(test_compatible);
	testsuite_add_test(test_machine);

	return testsuite_run();
}
