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

#include <assert.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>

// libarchive
#include <archive.h>
#include <archive_entry.h>

#include <pakfire/archive.h>
#include <pakfire/errno.h>
#include <pakfire/file.h>
#include <pakfire/util.h>

static void configure_archive(struct archive* a) {
	archive_read_support_filter_all(a);
	archive_read_support_format_all(a);	
}

static int archive_open(PakfireArchive archive, struct archive** a) {
	*a = archive_read_new();
	configure_archive(*a);

	if (archive_read_open_filename(*a, archive->path, PAKFIRE_ARCHIVE_BLOCKSIZE) == ARCHIVE_OK) {
		return 0;
	}

	archive_read_free(*a);
	*a = NULL;

	return -1;
}

static void archive_close(struct archive* a) {
	archive_read_close(a);
	archive_read_free(a);
}

static int archive_read(struct archive* a, void** data, size_t* data_size) {
	*data = NULL;
	*data_size = 0;

	for (;;) {
		*data = pakfire_realloc(*data, *data_size + PAKFIRE_ARCHIVE_BLOCKSIZE);

		ssize_t size = archive_read_data(a, *data + *data_size,
			PAKFIRE_ARCHIVE_BLOCKSIZE);

		if (size == 0)
			break;

		if (size < 0) {
			pakfire_free(*data);
			*data = NULL;

			return 1;
		}

		*data_size += size;
	}

	return 0;
}

static int find_archive_entry(struct archive_entry** entry, struct archive* a, const char* filename) {
	int r;

	while ((r = archive_read_next_header(a, entry)) == ARCHIVE_OK) {
		const char* entry_name = archive_entry_pathname(*entry);

		if (strcmp(entry_name, filename) == 0) {
			return 0;
		}
	}

	*entry = NULL;
	return 1;
}

static ssize_t payload_archive_read(struct archive* a, void* client_data, const void** buf) {
	struct payload_archive_data* data = client_data;
	*buf = data->buffer;

	return archive_read_data(data->archive, data->buffer, sizeof(data->buffer));
}

static int payload_archive_close(struct archive* a, void* client_data) {
	struct payload_archive_data* data = client_data;

	pakfire_free(data);

	return ARCHIVE_OK;
}

static int payload_archive_open(struct archive** a, struct archive* source_archive) {
	*a = archive_read_new();
	configure_archive(*a);

	struct payload_archive_data* data = pakfire_calloc(1, sizeof(*data));
	data->archive = source_archive;

	archive_read_set_callback_data(*a, data);
	archive_read_set_read_callback(*a, payload_archive_read);
	archive_read_set_close_callback(*a, payload_archive_close);

	return archive_read_open1(*a);
}

PakfireArchive pakfire_archive_create() {
	PakfireArchive archive = pakfire_calloc(1, sizeof(*archive));
	if (archive) {
		archive->format = -1;
	}

	return archive;
}

void pakfire_archive_free(PakfireArchive archive) {
	if (archive->path)
		pakfire_free(archive->path);

	pakfire_free(archive);
}

static int pakfire_archive_parse_entry_format(PakfireArchive archive,
		struct archive* a, struct archive_entry* e) {
	char format[PAKFIRE_ARCHIVE_FORMAT_SIZE + 1];
	format[PAKFIRE_ARCHIVE_FORMAT_SIZE] = '\0';

	archive_read_data(a, &format, PAKFIRE_ARCHIVE_FORMAT_SIZE);
	archive->format = atoi(format);

	return (archive->format < 0);
}

static int pakfire_archive_parse_entry_metadata(PakfireArchive archive,
		struct archive* a, struct archive_entry* e) {
	void* data;
	size_t data_size;

	int r = archive_read(a, &data, &data_size);
	if (r) {
		return 1;
	}

	#warning actually parse this

	pakfire_free(data);

	return 0;
}

static int pakfire_archive_parse_entry_filelist(PakfireArchive archive,
		struct archive* a, struct archive_entry* e) {
	char* data;
	size_t data_size;

	int r = archive_read(a, (void**)&data, &data_size);
	if (r) {
		return 1;
	}

	// Terminate string.
	data[data_size] = '\0';

	if (data_size > 0) {
		archive->filelist = pakfire_file_parse_from_file(data, archive->format);
	}

	pakfire_free(data);

	return 0;
}

static int pakfire_archive_read_metadata(PakfireArchive archive, struct archive* a) {
	int ret;

	struct archive_entry* entry;
	while ((ret = archive_read_next_header(a, &entry)) == ARCHIVE_OK) {
		const char* entry_name = archive_entry_pathname(entry);

		/* The first file in a pakfire package file must be
		 * the pakfire-format file, so we know with what version of
		 * the package format we are dealing with.
		 */
		if (archive->format < 0) {
			if (strcmp(PAKFIRE_ARCHIVE_FN_FORMAT, entry_name) == 0) {
				ret = pakfire_archive_parse_entry_format(archive, a, entry);
				if (ret)
					return PAKFIRE_E_PKG_INVALID;

			} else {
				return PAKFIRE_E_PKG_INVALID;
			}

		// If the format is set, we can go on...
		} else {
			// Parse the metadata
			if (strcmp(PAKFIRE_ARCHIVE_FN_METADATA, entry_name) == 0) {
				ret = pakfire_archive_parse_entry_metadata(archive, a, entry);
				if (ret)
					return PAKFIRE_E_PKG_INVALID;

			// Parse the filelist
			} else if (strcmp(PAKFIRE_ARCHIVE_FN_FILELIST, entry_name) == 0) {
				ret = pakfire_archive_parse_entry_filelist(archive, a, entry);
				if (ret)
					return PAKFIRE_E_PKG_INVALID;
			}
		}
	}

	return 0;
}

static int archive_copy_data(struct archive* in, struct archive* out) {
	int r;
	const void* buff;

	size_t size;
	off_t offset;

	for (;;) {
		r = archive_read_data_block(in, &buff, &size, &offset);
		if (r == ARCHIVE_EOF)
			break;

		if (r != ARCHIVE_OK)
			return r;

		r = archive_write_data_block(out, buff, size, offset);
		if (r != ARCHIVE_OK)
			return r;
	}

	return 0;
}

static int archive_extract(struct archive* a, const char* prefix) {
	struct archive_entry* entry;
	int r;

	// Unpack to the root filesystem if no prefix is given.
	if (!prefix)
		prefix = "/";

	struct archive* ext = archive_write_disk_new();

	// Set flags for extracting contents.
	int flags = 0;
	flags |= ARCHIVE_EXTRACT_ACL;
	flags |= ARCHIVE_EXTRACT_FFLAGS;
	flags |= ARCHIVE_EXTRACT_OWNER;
	flags |= ARCHIVE_EXTRACT_PERM;
	flags |= ARCHIVE_EXTRACT_SPARSE;
	flags |= ARCHIVE_EXTRACT_TIME;
	flags |= ARCHIVE_EXTRACT_UNLINK;
	flags |= ARCHIVE_EXTRACT_XATTR;

	archive_write_disk_set_options(ext, flags);
	archive_write_disk_set_standard_lookup(ext);

	char* pathname = NULL;
	for (;;) {
		r = archive_read_next_header(a, &entry);

		// Reached the end of the archive.
		if (r == ARCHIVE_EOF)
			break;

		// Prepend the prefix to the path the file is extracted to.
		if (prefix) {
			const char* archive_pathname = archive_entry_pathname(entry);
			pathname = pakfire_path_join(prefix, archive_pathname);

			archive_entry_set_pathname(entry, pathname);
		}

		r = archive_write_header(ext, entry);
		if (r != ARCHIVE_OK)
			goto out;

		size_t size = archive_entry_size(entry);
		if (size > 0) {
			r = archive_copy_data(a, ext);

			if (r != ARCHIVE_OK)
				goto out;
		}

#warning need to handle extended attributes
#if 0
		const char* name;
		const void* data;
		size_t size;

		while (archive_entry_xattr_next(entry, &name, &data, &size) == ARCHIVE_OK) {
			printf("name=%s\n", name);
		}
#endif

		r = archive_write_finish_entry(ext);

		pakfire_free(pathname);
	}

out:
	archive_write_close(ext);
	archive_write_free(ext);

	return r;
}


PakfireArchive pakfire_archive_open(const char* path) {
	PakfireArchive archive = pakfire_archive_create();
	archive->path = pakfire_strdup(path);

	// Open the archive file for reading.
	struct archive* a;
	int r = archive_open(archive, &a);
	if (r) {
		pakfire_errno = r;
		goto error;
	}

	// Parse all entries in the archive.
	r = pakfire_archive_read_metadata(archive, a);
	if (r) {
		pakfire_errno = r;
		return NULL;
	}

	return archive;

error:
	if (a)
		archive_read_free(a);

	pakfire_archive_free(archive);

	return NULL;
}

static struct archive* archive_open_payload(struct archive* a) {
	struct archive_entry* entry;
	int r;

	r = find_archive_entry(&entry, a, PAKFIRE_ARCHIVE_FN_PAYLOAD);
	if (r) {
		pakfire_errno = r;
		return NULL;
	}

	struct archive* payload_archive;
	r = payload_archive_open(&payload_archive, a);
	if (r) {
		pakfire_errno = r;
		return NULL;
	}

	return payload_archive;
}

int pakfire_archive_read(PakfireArchive archive, const char* filename,
		void** data, size_t* data_size, int flags) {
	struct archive* a;
	struct archive* pa = NULL;
	struct archive_entry* entry;

	int r = archive_open(archive, &a);
	if (r) {
		pakfire_errno = r;
		goto out;
	}

	int use_payload = (flags & PAKFIRE_ARCHIVE_USE_PAYLOAD);

	if (use_payload) {
		pa = archive_open_payload(a);

		// Strip leading / from filenames, because the payload does
		// not have leading slashes.
		if (*filename == '/')
			filename++;
	}

	r = find_archive_entry(&entry, use_payload ? pa : a, filename);
	if (r) {
		goto out;
	}

	r = archive_read(use_payload ? pa : a, data, data_size);

out:
	if (pa)
		archive_close(pa);

	archive_close(a);

	return r;
}

int pakfire_archive_extract(PakfireArchive archive, const char* prefix, int flags) {
	struct archive* a;
	struct archive* pa = NULL;

	int r = archive_open(archive, &a);
	if (r) {
		pakfire_errno = r;
		return 1;
	}

	int use_payload = (flags & PAKFIRE_ARCHIVE_USE_PAYLOAD);

	if (use_payload)
		pa = archive_open_payload(a);

	r = archive_extract(use_payload ? pa : a, prefix);

	if (pa)
		archive_close(pa);

	archive_close(a);

	return r;
}

const char* pakfire_archive_get_path(PakfireArchive archive) {
	return archive->path;
}

unsigned int pakfire_archive_get_format(PakfireArchive archive) {
	return archive->format;
}

PakfireFile pakfire_archive_get_filelist(PakfireArchive archive) {
	return archive->filelist;
}
