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

#ifndef PAKFIRE_DB_H
#define PAKFIRE_DB_H

#include <pakfire/types.h>

struct pakfire_db;

enum {
	PAKFIRE_DB_READONLY  = 0,
	PAKFIRE_DB_READWRITE = (1 << 0),
};

int pakfire_db_open(struct pakfire_db** db, Pakfire pakfire, int flags);

struct pakfire_db* pakfire_db_ref(struct pakfire_db* db);
struct pakfire_db* pakfire_db_unref(struct pakfire_db* db);

int pakfire_db_add_package(struct pakfire_db* db, PakfirePackage pkg);
int pakfire_db_remove_package(struct pakfire_db* db, PakfirePackage pkg);

#endif /* PAKFIRE_DB_H */
