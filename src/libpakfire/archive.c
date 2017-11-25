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
#include <ctype.h>
#include <fcntl.h>
#include <gpgme.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>

// libarchive
#include <archive.h>
#include <archive_entry.h>

// libgcrypt
#include <gcrypt.h>

#include <pakfire/archive.h>
#include <pakfire/errno.h>
#include <pakfire/file.h>
#include <pakfire/i18n.h>
#include <pakfire/key.h>
#include <pakfire/pakfire.h>
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

static archive_checksum_t* pakfire_archive_checksum_create(const char* filename, const char* checksum, archive_checksum_algo_t algo) {
	archive_checksum_t* c = pakfire_calloc(1, sizeof(*c));
	if (c) {
		c->filename = pakfire_strdup(filename);
		c->checksum = pakfire_strdup(checksum);
		c->algo = algo;
	}

	return c;
}

static void pakfire_archive_checksum_free(archive_checksum_t* c) {
	pakfire_free(c->filename);
	pakfire_free(c->checksum);
	pakfire_free(c);
}

static archive_checksum_t* pakfire_archive_checksum_find(PakfireArchive archive, const char* filename) {
	archive_checksum_t** checksums = archive->checksums;

	while (checksums && *checksums) {
		archive_checksum_t* checksum = *checksums++;

		if (strcmp(checksum->filename, filename) == 0)
			return checksum;
	}

	// Nothing found
	return NULL;
}

static archive_signature_t* pakfire_archive_signature_create(const char* sigdata) {
	archive_signature_t* s = pakfire_calloc(1, sizeof(*s));
	if (s) {
		s->sigdata = pakfire_strdup(sigdata);
	}

	return s;
}

static void pakfire_archive_signature_free(archive_signature_t* s) {
	pakfire_free(s->sigdata);
	pakfire_free(s);
}

size_t pakfire_archive_count_signatures(PakfireArchive archive) {
	size_t i = 0;

	archive_signature_t** signatures = archive->signatures;
	while (signatures && *signatures++) {
		i++;
	}

	return i;
}

PakfireArchive pakfire_archive_create(Pakfire pakfire) {
	PakfireArchive archive = pakfire_calloc(1, sizeof(*archive));
	if (archive) {
		archive->pakfire = pakfire_ref(pakfire);
		archive->format = -1;

		archive->signatures = NULL;
	}

	return archive;
}

void pakfire_archive_free(PakfireArchive archive) {
	if (archive->path)
		pakfire_free(archive->path);

	// Free checksums
	archive_checksum_t** checksums = archive->checksums;
	while (checksums && *checksums)
		pakfire_archive_checksum_free(*checksums++);

	// Free signatures
	archive_signature_t** signatures = archive->signatures;
	while (signatures && *signatures)
		pakfire_archive_signature_free(*signatures++);

	pakfire_unref(archive->pakfire);
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

static int pakfire_archive_parse_entry_checksums(PakfireArchive archive,
		struct archive* a, struct archive_entry* e) {
	char* data;
	size_t data_size;

	int r = archive_read(a, (void**)&data, &data_size);
	if (r)
		return 1;

	// Empty file
	if (data_size <= 0)
		return 1;

	// Terminate string.
	data[data_size] = '\0';

	// Allocate some space to save the checksums
	archive_checksum_t** checksums = archive->checksums = pakfire_calloc(10, sizeof(*archive->checksums));

	const char* filename = NULL;
	const char* checksum = NULL;
	archive_checksum_algo_t algo = PAKFIRE_CHECKSUM_SHA512;

	char* p = data;
	while (*p) {
		// Filename starts here
		filename = p;

		// Find end of filename
		while (!isspace(*p))
			p++;

		// Terminate filename
		*p++ = '\0';

		// Skip any spaces
		while (isspace(*p))
			p++;

		// Checksum starts here
		checksum = p;

		// Find end of checksum
		while (!isspace(*p))
			p++;

		// Terminate the checksum
		*p++ = '\0';

		// Add new checksum object
		if (filename && checksum) {
			*checksums++ = pakfire_archive_checksum_create(filename, checksum, algo);
		}

		// Eat up any space before next thing starts
		while (isspace(*p))
			p++;
	}

	// Terminate the list
	*checksums = NULL;

	pakfire_free(data);

	return 0;
}

static int pakfire_archive_parse_entry_signature(PakfireArchive archive,
		struct archive* a, struct archive_entry* e) {
	char* data;
	size_t data_size;

	int r = archive_read(a, (void**)&data, &data_size);
	if (r)
		return 1;

	// Terminate string.
	data[data_size] = '\0';

	archive_signature_t* signature = pakfire_archive_signature_create(data);
	if (!signature)
		return 1;

	if (archive->signatures) {
		// Count signatures
		size_t num_signatures = pakfire_archive_count_signatures(archive) + 1;

		// Resize the array
		archive->signatures = pakfire_realloc(archive->signatures, sizeof(*archive->signatures) * num_signatures);
	} else {
		archive->signatures = pakfire_calloc(2, sizeof(*archive->signatures));
	}

	// Look for last element
	archive_signature_t** signatures = archive->signatures;
	while (*signatures) {
		*signatures++;
	}

	// Append signature
	*signatures++ = signature;

	// Terminate list
	*signatures = NULL;

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

			// Parse the checksums
			} else if (strcmp(PAKFIRE_ARCHIVE_FN_CHECKSUMS, entry_name) == 0) {
				ret = pakfire_archive_parse_entry_checksums(archive, a, entry);
				if (ret)
					return PAKFIRE_E_PKG_INVALID;

			// Parse signatures
			} else if (strncmp(PAKFIRE_ARCHIVE_FN_SIGNATURES, entry_name, strlen(PAKFIRE_ARCHIVE_FN_SIGNATURES)) == 0) {
				ret = pakfire_archive_parse_entry_signature(archive, a, entry);
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


PakfireArchive pakfire_archive_open(Pakfire pakfire, const char* path) {
	PakfireArchive archive = pakfire_archive_create(pakfire);
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

char** pakfire_archive_get_signatures(PakfireArchive archive) {
	size_t size = pakfire_archive_count_signatures(archive);

	char** head = pakfire_calloc(size, sizeof(*head));
	if (!head)
		return NULL;

	char** list = head;
	archive_signature_t** signatures = archive->signatures;
	while (signatures && *signatures) {
		archive_signature_t* signature = *signatures++;

		*list++ = pakfire_strdup(signature->sigdata);
	}

	// Terminate list
	*list = NULL;

	return head;
}

static pakfire_archive_verify_status_t pakfire_archive_verify_checksums(PakfireArchive archive) {
	pakfire_archive_verify_status_t status = PAKFIRE_ARCHIVE_VERIFY_INVALID;

	// Cannot validate anything if no signatures are available
	archive_signature_t** signatures = archive->signatures;
	if (!signatures)
		return PAKFIRE_ARCHIVE_VERIFY_OK;

	char* data = NULL;
	size_t size = 0;
	gpgme_error_t error;

	// Load the checksums file
	int r = pakfire_archive_read(archive, PAKFIRE_ARCHIVE_FN_CHECKSUMS,
		(void *)&data, &size, 0);
	if (r)
		return status;

	// Convert into gpgme data object
	gpgme_data_t signed_text;
	error = gpgme_data_new_from_mem(&signed_text, data, size, 0);
	if (error != GPG_ERR_NO_ERROR)
		return -1;

	// Get GPG context
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(archive->pakfire);

	// Try for each signature
	while (signatures && *signatures) {
		archive_signature_t* signature = *signatures++;

		gpgme_data_t sigdata;
		error = gpgme_data_new_from_mem(&sigdata, signature->sigdata, strlen(signature->sigdata), 0);
		if (error != GPG_ERR_NO_ERROR)
			continue;

		// Perform verification
		error = gpgme_op_verify(gpgctx, sigdata, signed_text, NULL);
		if (error != GPG_ERR_NO_ERROR)
			goto CLEANUP;

		// Run the operation
		gpgme_verify_result_t result = gpgme_op_verify_result(gpgctx);

		// Check if any signatures have been returned
		if (!result || !result->signatures)
			goto CLEANUP;

		// Walk through all signatures
		for (gpgme_signature_t sig = result->signatures; sig; sig = sig->next) {
			switch (gpg_err_code(sig->status)) {
				// All good
				case GPG_ERR_NO_ERROR:
					status = PAKFIRE_ARCHIVE_VERIFY_OK;
					break;

				// Key has expired (still good)
				case GPG_ERR_KEY_EXPIRED:
					status = PAKFIRE_ARCHIVE_VERIFY_KEY_EXPIRED;
					break;

				// Signature has expired (bad)
				case GPG_ERR_SIG_EXPIRED:
					status = PAKFIRE_ARCHIVE_VERIFY_SIG_EXPIRED;
					break;

				// We don't have the key
				case GPG_ERR_NO_PUBKEY:
					status = PAKFIRE_ARCHIVE_VERIFY_KEY_UNKNOWN;
					break;

				// Bad signature (or any other errors)
				case GPG_ERR_BAD_SIGNATURE:
				default:
					status = PAKFIRE_ARCHIVE_VERIFY_INVALID;
					break;
			}
		}

CLEANUP:
		gpgme_data_release(sigdata);
	}

	gpgme_data_release(signed_text);
	gpgme_release(gpgctx);

	return status;
}

static char* digest_to_hexdigest(const unsigned char* digest, unsigned int len) {
	char* hexdigest = pakfire_calloc(len * 2, sizeof(*hexdigest));

	char* p = hexdigest;
	for (unsigned int i = 0; i < len; i++) {
		snprintf(p, 3, "%02x", digest[i]);
		p += 2;
	}

	return hexdigest;
}

static pakfire_archive_verify_status_t pakfire_archive_verify_file(struct archive* a, const archive_checksum_t* checksum) {
	pakfire_archive_verify_status_t status = PAKFIRE_ARCHIVE_VERIFY_INVALID;

	// Make sure libgcrypt is initialized
	init_libgcrypt();

	int algo = 0;
	switch (checksum->algo) {
		case PAKFIRE_CHECKSUM_SHA512:
			algo = GCRY_MD_SHA512;
			break;

		case PAKFIRE_CHECKSUM_UNKNOWN:
			break;
	}
	assert(algo);

	gcry_md_hd_t hd = NULL;
	gcry_error_t error = gcry_md_open(&hd, algo, 0);
	if (error != GPG_ERR_NO_ERROR)
		return PAKFIRE_ARCHIVE_VERIFY_ERROR;

	const void* buff;
	size_t size;
	off_t offset;

	for (;;) {
		int r = archive_read_data_block(a, &buff, &size, &offset);
		if (r == ARCHIVE_EOF)
			break;

		if (r != ARCHIVE_OK) {
			pakfire_errno = r;
			status = PAKFIRE_ARCHIVE_VERIFY_ERROR;
			goto FAIL;
		}

		// Update hash digest
		gcry_md_write(hd, buff, size);
	}

	// Finish computing the hash
	gcry_md_final(hd);

	// Get the hash digest
	unsigned int l = gcry_md_get_algo_dlen(algo);
	unsigned char* digest = gcry_md_read(hd, algo);

	// Convert to hexdigest
	char* hexdigest = digest_to_hexdigest(digest, l);

	// Compare digests
	if (strcmp(checksum->checksum, hexdigest) == 0)
		status = PAKFIRE_ARCHIVE_VERIFY_OK;

	pakfire_free(hexdigest);

FAIL:
	gcry_md_close(hd);

	return status;
}

pakfire_archive_verify_status_t pakfire_archive_verify(PakfireArchive archive) {
	// Verify that checksums file is signed with a valid key
	pakfire_archive_verify_status_t status = pakfire_archive_verify_checksums(archive);
	if (status)
		return status;

	// Open the archive file
	struct archive* a;
	int r = archive_open(archive, &a);
	if (r) {
		pakfire_errno = r;
		return PAKFIRE_ARCHIVE_VERIFY_ERROR;
	}

	struct archive_entry* entry;
	while ((r = archive_read_next_header(a, &entry)) == ARCHIVE_OK) {
		const char* entry_name = archive_entry_pathname(entry);

		// See if we have a checksum for this file
		const archive_checksum_t* checksum = pakfire_archive_checksum_find(archive, entry_name);
		if (!checksum)
			continue;

		// Compare the checksums
		status = pakfire_archive_verify_file(a, checksum);
		if (status)
			return status;
	}

	return PAKFIRE_ARCHIVE_VERIFY_OK;
}

const char* pakfire_archive_verify_strerror(pakfire_archive_verify_status_t status) {
	switch (status) {
		case PAKFIRE_ARCHIVE_VERIFY_OK:
			return _("Verify OK");

		case PAKFIRE_ARCHIVE_VERIFY_ERROR:
			return _("Error performing validation");

		case PAKFIRE_ARCHIVE_VERIFY_INVALID:
			return _("Invalid signature");

		case PAKFIRE_ARCHIVE_VERIFY_SIG_EXPIRED:
			return _("Signature expired");

		case PAKFIRE_ARCHIVE_VERIFY_KEY_EXPIRED:
			return _("Key expired");

		case PAKFIRE_ARCHIVE_VERIFY_KEY_UNKNOWN:
			return _("Key unknown");
	}

	return NULL;
}
