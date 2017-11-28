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

#include "testsuite.h"

int test_run(const test_t* t) {
	LOG("running %s\n", t->name);

	int r = t->func(t);

	return r;
}

testsuite_t* testsuite_create(size_t n) {
	testsuite_t* ts = calloc(1, sizeof(*ts));
	if (!ts)
		exit(EXIT_FAILURE);

	// Make space for n tests
	ts->tests = calloc(n + 1, sizeof(*ts->tests));
	ts->left = n;

	return ts;
};

int testsuite_add_test(testsuite_t* ts, const char* name, test_function_t* func) {
	if (ts->left == 0)
		exit(EXIT_FAILURE);

	test_t** last = ts->tests;
	while (*last)
		last++;

	test_t* test = *last = calloc(1, sizeof(**last));
	if (test) {
		test->name = name;
		test->func = func;
	}

	ts->left--;

	return 0;
}

int testsuite_run(testsuite_t* ts) {
	for (test_t** t = ts->tests; *t; t++) {
		int r = test_run(*t);
		if (r)
			exit(r);
	}

	return EXIT_SUCCESS;
}
