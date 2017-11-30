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

#include "../testsuite.h"

#include <pakfire/key.h>

#include "key.h"
#include "pakfire.h"

int test_init(const test_t* t) {
	Pakfire pakfire = init_pakfire();
	if (!pakfire)
		return EXIT_FAILURE;

	// Try loading any keys & delete them all
	PakfireKey* keys = pakfire_key_list(pakfire);
	while (keys && *keys) {
		PakfireKey key = *keys++;

		pakfire_key_delete(key);
		pakfire_key_unref(key);
	}

	// Load list of keys again
	keys = pakfire_key_list(pakfire);

	// Must be empty now
	assert_return(keys == NULL, EXIT_FAILURE);

	return EXIT_SUCCESS;
}

int test_import(const test_t* t) {
	Pakfire pakfire = init_pakfire();
	if (!pakfire)
		return EXIT_FAILURE;

	// Try to delete the key just in case it
	// has been imported before
	PakfireKey key = pakfire_key_get(pakfire, TEST_KEY_FINGERPRINT);
	if (key) {
		pakfire_key_delete(key);
		pakfire_key_unref(key);
	}

	// Import a key
	PakfireKey* keys = pakfire_key_import(pakfire, TEST_KEY_DATA);

	// We should have a list with precisely one key object
	assert_return(keys, EXIT_FAILURE);
	assert_return(keys[0] != NULL, EXIT_FAILURE);
	assert_return(keys[1] == NULL, EXIT_FAILURE);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_init();

	testsuite_t* ts = testsuite_create(2);

	testsuite_add_test(ts, "test_init", test_init);
	testsuite_add_test(ts, "test_import", test_import);

	return testsuite_run(ts);
}
