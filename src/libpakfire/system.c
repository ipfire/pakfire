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
#include <sys/utsname.h>

#include <pakfire/constants.h>
#include <pakfire/system.h>
#include <pakfire/util.h>

const char* system_machine() {
    static const char* __system_machine = NULL;

    if (!__system_machine) {
        struct utsname buf;

        int r = uname(&buf);
        if (r)
            return NULL;

        __system_machine = pakfire_strdup(buf.machine);
    }

    return __system_machine;
}
