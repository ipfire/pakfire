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

#include <pakfire/key.h>
#include <pakfire/util.h>

#include "../testsuite.h"
#include "key.h"

static int test_init(const struct test* t) {
	// Try loading any keys & delete them all
	PakfireKey* keys = pakfire_key_list(t->pakfire);
	while (keys && *keys) {
		PakfireKey key = *keys++;

		pakfire_key_delete(key);
		pakfire_key_unref(key);
	}

	// Load list of keys again
	keys = pakfire_key_list(t->pakfire);

	// Must be empty now
	ASSERT(keys == NULL);

	return EXIT_SUCCESS;
}

static int test_import_export(const struct test* t) {
	// Try to delete the key just in case it
	// has been imported before
	PakfireKey key = pakfire_key_get(t->pakfire, TEST_KEY_FINGERPRINT);
	if (key) {
		pakfire_key_delete(key);
		pakfire_key_unref(key);
	}

	// Import a key
	PakfireKey* keys = pakfire_key_import(t->pakfire, TEST_KEY_DATA);

	// We should have a list with precisely one key object
	ASSERT(keys);
	ASSERT(keys[0] != NULL);
	ASSERT(keys[1] == NULL);

	// Get the imported key
	key = *keys;

	// Check the fingerprint
	const char* fingerprint = pakfire_key_get_fingerprint(key);
	ASSERT(strcmp(fingerprint, TEST_KEY_FINGERPRINT) == 0);

	// Dump key description
	char* dump = pakfire_key_dump(key);
	ASSERT(dump);
	LOG("%s\n", dump);
	pakfire_free(dump);

	// Export the key
	char* data = pakfire_key_export(key, 0);
	ASSERT(data);

	LOG("Exported key:\n%s\n", data);
	pakfire_free(data);

	pakfire_key_unref(key);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_add_test(test_init);
	testsuite_add_test(test_import_export);

	return testsuite_run();
}
