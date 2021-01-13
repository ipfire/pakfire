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

int test_init(const test_t* t) {
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
	assert_return(keys == NULL, EXIT_FAILURE);

	return EXIT_SUCCESS;
}

int test_import(const test_t* t) {
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
	assert_return(keys, EXIT_FAILURE);
	assert_return(keys[0] != NULL, EXIT_FAILURE);
	assert_return(keys[1] == NULL, EXIT_FAILURE);

	// Get the imported key
	key = *keys;

	// Check the fingerprint
	const char* fingerprint = pakfire_key_get_fingerprint(key);
	assert_return(strcmp(fingerprint, TEST_KEY_FINGERPRINT) == 0, EXIT_FAILURE);

	pakfire_key_unref(key);

	return EXIT_SUCCESS;
}

int test_export(const test_t* t) {
	PakfireKey key = pakfire_key_get(t->pakfire, TEST_KEY_FINGERPRINT);
	assert_return(key, EXIT_FAILURE);

	// Dump key description
	char* dump = pakfire_key_dump(key);
	assert_return(dump, EXIT_FAILURE);
	LOG("%s\n", dump);
	pakfire_free(dump);

	char* data = pakfire_key_export(key, 0);
	assert_return(data, EXIT_FAILURE);

	LOG("Exported key:\n%s\n", data);
	pakfire_free(data);

	pakfire_key_unref(key);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_add_test(test_init);
	testsuite_add_test(test_import);
	testsuite_add_test(test_export);

	return testsuite_run();
}
