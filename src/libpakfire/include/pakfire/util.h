/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2013 Pakfire development team                                 #
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

#ifndef PAKFIRE_UTIL_H
#define PAKFIRE_UTIL_H

#include <stddef.h>

void pakfire_oom(size_t num, size_t len);

void* pakfire_malloc(size_t len);
void* pakfire_calloc(size_t num, size_t len);
void* pakfire_realloc(void* ptr, size_t size);

void* pakfire_free(void* mem);

char* pakfire_strdup(const char* s);

char* pakfire_format_size(double size);

char* pakfire_path_join(const char* first, const char* second);

char* pakfire_basename(const char* path);
char* pakfire_dirname(const char* path);

char* pakfire_sgets(char* str, int num, char** input);
char* pakfire_remove_trailing_newline(char* str);

#endif /* PAKFIRE_UTIL_H */