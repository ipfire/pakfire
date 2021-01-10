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

#include <pakfire/parser.h>
#include <pakfire/util.h>

#include "../testsuite.h"

int test_parse(const test_t* t) {
	char* path = pakfire_path_join(TEST_SRC_PATH, "data/kernel.nm");

	// Open file
	FILE* f = fopen(path, "r");
	assert_return(f, EXIT_FAILURE);

	PakfireParser parser = pakfire_parser_create(t->pakfire, NULL, NULL);

	int r = pakfire_parser_read(parser, f);
	assert_return(r == 0, EXIT_FAILURE);

	// Try to retrieve some value
	char* value = pakfire_parser_get(parser, "sources");
	assert_return(value, EXIT_FAILURE);

	printf("VALUE: sources = %s\n", value);
	pakfire_free(value);

	// Cleanup
	pakfire_free(path);

	pakfire_parser_unref(parser);

	return EXIT_SUCCESS;
}

int main(int argc, char** argv) {
	testsuite_t* ts = testsuite_create(1);

	testsuite_add_test(ts, "test_parse", test_parse);

	return testsuite_run(ts);
}
