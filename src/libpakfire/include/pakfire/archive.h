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

#ifndef PAKFIRE_ARCHIVE_H
#define PAKFIRE_ARCHIVE_H

#include <archive.h>

#include <pakfire/types.h>

PakfireArchive pakfire_archive_create();
void pakfire_archive_free(PakfireArchive archive);

PakfireArchive pakfire_archive_open(const char* path);

int pakfire_archive_read(PakfireArchive archive, const char* filename,
	void** data, size_t* data_size, int flags);
int pakfire_archive_extract(PakfireArchive archive, const char* prefix, int flags);

const char* pakfire_archive_get_path(PakfireArchive archive);

unsigned int pakfire_archive_get_format(PakfireArchive archive);

PakfireFile pakfire_archive_get_filelist(PakfireArchive archive);

enum pakfire_archive_flags {
	PAKFIRE_ARCHIVE_USE_PAYLOAD = 1 << 0,
};

#define PAKFIRE_ARCHIVE_FN_FILELIST			"filelist"
#define PAKFIRE_ARCHIVE_FN_FORMAT			"pakfire-format"
#define PAKFIRE_ARCHIVE_FN_METADATA			"info"
#define PAKFIRE_ARCHIVE_FN_PAYLOAD			"data.img"

#ifdef PAKFIRE_PRIVATE

#define PAKFIRE_ARCHIVE_BLOCKSIZE			10240
#define PAKFIRE_ARCHIVE_FORMAT_SIZE			5

struct _PakfireArchive {
	char* path;

	// metadata
	int format;

	PakfireFile filelist;
};

struct payload_archive_data {
	struct archive* archive;
	char buffer[PAKFIRE_ARCHIVE_BLOCKSIZE];
};

#endif

#endif /* PAKFIRE_ARCHIVE_H */
