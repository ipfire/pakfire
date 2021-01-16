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

#ifndef PAKFIRE_EXECUTE_H
#define PAKFIRE_EXECUTE_H

#include <pakfire/types.h>

struct pakfire_execute_logger {
	int (*log_stdout)(Pakfire pakfire, const char* data);
	int (*log_stderr)(Pakfire pakfire, const char* data);
};

int pakfire_execute(Pakfire pakfire, const char* argv[], char* envp[],
	int flags, struct pakfire_execute_logger* logger);
int pakfire_execute_command(Pakfire pakfire, const char* command, char* envp[],
	int flags, struct pakfire_execute_logger* logger);

enum {
	PAKFIRE_EXECUTE_NONE			= 0,
	PAKFIRE_EXECUTE_ENABLE_NETWORK	= (1 << 0),
	PAKFIRE_EXECUTE_INTERACTIVE     = (1 << 1),
};

#endif /* PAKFIRE_EXECUTE_H */
