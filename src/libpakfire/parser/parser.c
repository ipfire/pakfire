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

#include <pakfire/errno.h>
#include <pakfire/parser.h>
#include <pakfire/util.h>

struct pakfire_parser_declaration** pakfire_parser_parse_metadata_from_file(
		Pakfire pakfire, FILE* f) {
	char* data;
	size_t len;

	int r = pakfire_read_file_into_buffer(f, &data, &len);
	if (r) {
		pakfire_errno = r;
		return NULL;
	}

	struct pakfire_parser_declaration** declarations = \
		pakfire_parser_parse_metadata(pakfire, data, len);

	if (data)
		pakfire_free(data);

	return declarations;
}
