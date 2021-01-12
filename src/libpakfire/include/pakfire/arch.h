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

#ifndef PAKFIRE_ARCH_H
#define PAKFIRE_ARCH_H

int pakfire_arch_supported(const char* name);
const char* pakfire_arch_platform(const char* name);
unsigned long pakfire_arch_personality(const char* name);
char* pakfire_arch_machine(const char* arch, const char* vendor);
const char* pakfire_arch_native();
int pakfire_arch_is_compatible(const char* name, const char* compatible_arch);
int pakfire_arch_supported_by_host(const char* name);

#endif /* PAKFIRE_ARCH_H */
