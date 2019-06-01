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

#ifndef PAKFIRE_PARSER_H
#define PAKFIRE_PARSER_H

#include <stdio.h>

#include <pakfire/types.h>

PakfireParser pakfire_parser_create(Pakfire pakfire, PakfireParser parser,
	const char* namespace);
PakfireParser pakfire_parser_ref(PakfireParser parser);
PakfireParser pakfire_parser_unref(PakfireParser parser);
PakfireParser pakfire_parser_get_parent(PakfireParser parser);

int pakfire_parser_set(PakfireParser parser,
		const char* name, const char* value);
int pakfire_parser_append(PakfireParser parser,
	const char* name, const char* value);

char* pakfire_parser_expand(PakfireParser parser, const char* value);
char* pakfire_parser_get(PakfireParser parser, const char* name);

PakfireParser pakfire_parser_merge(PakfireParser parser1, PakfireParser parser2);

int pakfire_parser_read(PakfireParser parser, FILE* f);
char* pakfire_parser_dump(PakfireParser parser);

#ifdef PAKFIRE_PRIVATE

Pakfire pakfire_parser_get_pakfire(PakfireParser parser);

struct pakfire_parser_declaration {
	char* name;
	char* value;
};

struct pakfire_parser_declarations {
	struct pakfire_parser_declaration** declarations;
	unsigned int next;
	unsigned int num;
};

int pakfire_parser_parse_data(PakfireParser parser, const char* data, size_t len);

#endif /* PAKFIRE_PRIVATE */

#endif /* PAKFIRE_PARSER_H */
