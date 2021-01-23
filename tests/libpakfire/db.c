/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2021 Pakfire development team                                 #
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

#include <pakfire/db.h>
#include <pakfire/util.h>

#include "../testsuite.h"

static int test_open_ro(const struct test* t) {
	struct pakfire_db* db;

	int r = pakfire_db_open(&db, t->pakfire, PAKFIRE_DB_READONLY);
	ASSERT(!r);

	pakfire_db_unref(db);

	return 0;
}

static int test_open_rw(const struct test* t) {
	struct pakfire_db* db;

	int r = pakfire_db_open(&db, t->pakfire, PAKFIRE_DB_READWRITE);
	ASSERT(!r);

	pakfire_db_unref(db);

	return 0;
}

static int test_check(const struct test* t) {
	struct pakfire_db* db;

	int r = pakfire_db_open(&db, t->pakfire, PAKFIRE_DB_READWRITE);
	ASSERT(!r);

	// Perform check
	ASSERT(!pakfire_db_check(db));

	pakfire_db_unref(db);

	return 0;
}

int main(int argc, char** argv) {
	testsuite_add_test(test_open_ro);
	testsuite_add_test(test_open_rw);
	testsuite_add_test(test_check);

	return testsuite_run();
}
