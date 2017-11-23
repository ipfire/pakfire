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

#ifndef PAKFIRE_ERRNO_H
#define PAKFIRE_ERRNO_H

enum _pakfire_errors {
	PAKFIRE_E_FAILED = 1,					// general runtime error
	PAKFIRE_E_OP,							// client programming error
	PAKFIRE_E_LIBSOLV,						// error propagated from libsolv
	PAKFIRE_E_IO,							// I/O error
	PAKFIRE_E_ARCH,
	PAKFIRE_E_SELECTOR,
	PAKFIRE_E_PKG_INVALID,					// when a package is not in the pakfire format
	PAKFIRE_E_EOF,
	PAKFIRE_E_SOLV_NOT_SOLV,				// SOLV file in not in SOLV format
	PAKFIRE_E_SOLV_UNSUPPORTED,				// SOLV file is in an unsupported format
	PAKFIRE_E_SOLV_CORRUPTED,				// SOLV file is corrupted
	PAKFIRE_E_INVALID_INPUT,
};

extern __thread int pakfire_errno;

int pakfire_get_errno(void);

#endif /* PAKFIRE_ERRNO_H */
