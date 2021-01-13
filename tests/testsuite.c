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

#include <linux/limits.h>
#include <stdlib.h>

#include "testsuite.h"

#include <pakfire/logging.h>
#include <pakfire/pakfire.h>

const char* TEST_SRC_PATH = ABS_TOP_SRCDIR "/tests";

struct testsuite ts;

static int test_run(struct test* t) {
	char root[PATH_MAX];
	int r;

	// Create test root directory
	snprintf(root, PATH_MAX - 1, "%s/pakfire-test-XXXXXX", TEST_ROOTFS);
	char* tmp = mkdtemp(root);
	ASSERT(root == tmp);

	LOG("running %s (%s)\n", t->name, root);

	// Create a pakfire instance
	r = pakfire_create(&t->pakfire, root, NULL);
	if (r) {
		LOG("ERROR: Could not initialize Pakfire: %s\n", strerror(-r));
		exit(1);
	}

	ASSERT(t->pakfire);

	// Log to stderr
	pakfire_log_set_function(t->pakfire, pakfire_log_stderr);

	// Enable debug logging
	pakfire_log_set_priority(t->pakfire, LOG_DEBUG);

	r = t->func(t);
	if (r)
		LOG("Test failed with error code: %d\n", r);

	// Release pakfire
	Pakfire p = pakfire_unref(t->pakfire);

	// Check if Pakfire was actually released
	if (p) {
		LOG("Error: Pakfire instance was not released\n");
		return 1;
	}

	// Cleanup root
	// TODO

	return r;
}

int __testsuite_add_test(const char* name, int (*func)(const struct test* t)) {
	// Check if any space is left
	if (ts.num >= MAX_TESTS) {
		LOG("ERROR: We are out of space for tests\n");
		exit(EXIT_FAILURE);
	}

	struct test* test = &ts.tests[ts.num++];

	// Set parameters
	test->name = name;
	test->func = func;

	return 0;
}

int testsuite_run() {
	for (unsigned int i = 0; i < ts.num; i++) {
		int r = test_run(&ts.tests[i]);
		if (r)
			exit(r);
	}

	return EXIT_SUCCESS;
}
