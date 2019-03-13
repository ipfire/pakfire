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

#include <stddef.h>

#include <pakfire/types.h>

typedef enum pakfire_archive_verify_status {
	PAKFIRE_ARCHIVE_VERIFY_OK = 0,
	PAKFIRE_ARCHIVE_VERIFY_NO_SIGNATURES,
	PAKFIRE_ARCHIVE_VERIFY_INVALID,
	PAKFIRE_ARCHIVE_VERIFY_SIG_EXPIRED,
	PAKFIRE_ARCHIVE_VERIFY_KEY_EXPIRED,
	PAKFIRE_ARCHIVE_VERIFY_KEY_UNKNOWN,
	PAKFIRE_ARCHIVE_VERIFY_ERROR,
} pakfire_archive_verify_status_t;

typedef enum pakfire_archive_flags {
	PAKFIRE_ARCHIVE_USE_PAYLOAD = 1 << 0,
} pakfire_archive_flags_t;

PakfireArchive pakfire_archive_create(Pakfire pakfire);
PakfireArchive pakfire_archive_ref(PakfireArchive archive);
PakfireArchive pakfire_archive_unref(PakfireArchive archive);

PakfireArchive pakfire_archive_open(Pakfire pakfire, const char* path);

int pakfire_archive_read(PakfireArchive archive, const char* filename,
	void** data, size_t* data_size, int flags);
int pakfire_archive_extract(PakfireArchive archive, const char* prefix, int flags);

const char* pakfire_archive_get_path(PakfireArchive archive);

unsigned int pakfire_archive_get_format(PakfireArchive archive);

PakfireFile pakfire_archive_get_filelist(PakfireArchive archive);

pakfire_archive_verify_status_t pakfire_archive_verify(PakfireArchive archive);
const char* pakfire_archive_verify_strerror(pakfire_archive_verify_status_t status);

size_t pakfire_archive_count_signatures(PakfireArchive archive);
PakfireArchiveSignature* pakfire_archive_get_signatures(PakfireArchive archive);

PakfireArchiveSignature pakfire_archive_signature_ref(PakfireArchiveSignature signature);
void pakfire_archive_signature_unref(PakfireArchiveSignature signature);
const char* pakfire_archive_signature_get_data(PakfireArchiveSignature signature);

#define PAKFIRE_ARCHIVE_FN_CHECKSUMS		"chksums"
#define PAKFIRE_ARCHIVE_FN_FILELIST			"filelist"
#define PAKFIRE_ARCHIVE_FN_FORMAT			"pakfire-format"
#define PAKFIRE_ARCHIVE_FN_METADATA			"info"
#define PAKFIRE_ARCHIVE_FN_PAYLOAD			"data.img"
#define PAKFIRE_ARCHIVE_FN_SIGNATURES		"signatures"

#ifdef PAKFIRE_PRIVATE

typedef enum archive_checksum_algo {
	PAKFIRE_CHECKSUM_UNKNOWN = 0,
	PAKFIRE_CHECKSUM_SHA512,
} archive_checksum_algo_t;

#endif

#endif /* PAKFIRE_ARCHIVE_H */
