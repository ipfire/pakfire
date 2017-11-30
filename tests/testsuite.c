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

#include <pakfire/logging.h>
#include <pakfire/pakfire.h>

const char* TEST_SRC_PATH = ABS_TOP_SRCDIR "/tests";
const char* TEST_PATH = ABS_TOP_BUILDDIR "/tests/.data";

int testsuite_init() {
	// Initialize the pakfire library
	int r = pakfire_init();
	if (r)
		return r;

	// Log to stderr
	pakfire_log_set_function(pakfire_log_stderr);

	return 0;
}

static int test_run(test_t* t) {
	LOG("running %s\n", t->name);

	t->pakfire = pakfire_create(TEST_PATH, NULL);
	assert_return(t->pakfire, EXIT_FAILURE);

	int r = t->func(t);
	if (r)
		LOG("Test failed with error code: %d\n", r);

	// Release pakfire
	pakfire_unref(t->pakfire);

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

int testsuite_add_test(testsuite_t* ts, const char* name, test_function_t func) {
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
