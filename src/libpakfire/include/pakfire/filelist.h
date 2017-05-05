/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2014 Pakfire development team                                 #
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

#ifndef PAKFIRE_FILELIST_H
#define PAKFIRE_FILELIST_H

#include <pakfire/types.h>

PakfireFilelist pakfire_filelist_create(PakfirePackage pkg);
void pakfire_filelist_free(PakfireFilelist list);


#ifdef PAKFIRE_PRIVATE

struct _PakfireFilelist {
	PakfirePackage pkg;

	PakfireFile first;
	PakfireFile last;
};

#endif

#endif /* PAKFIRE_FILELIST_H */