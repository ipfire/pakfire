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

#include <assert.h>
#include <gpgme.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include <pakfire/constants.h>
#include <pakfire/errno.h>
#include <pakfire/i18n.h>
#include <pakfire/key.h>
#include <pakfire/logging.h>
#include <pakfire/pakfire.h>
#include <pakfire/util.h>

#define DEFAULT_KEY_SIZE "rsa4096"

gpgme_ctx_t pakfire_get_gpgctx(Pakfire pakfire) {
	static int gpg_initialized = 0;
	gpgme_error_t error;
	const char* error_string;

	if (!gpg_initialized) {
		// Initialise gpgme
		const char* version = gpgme_check_version(NULL);
		DEBUG("Loaded gpgme %s\n", version);

		// Check if we support GPG
		error = gpgme_engine_check_version(GPGME_PROTOCOL_OpenPGP);
		if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
			goto FAIL;

		// GPG has been initialized
		gpg_initialized++;
	}

	// Create a new context
	gpgme_ctx_t ctx;
	error = gpgme_new(&ctx);
	if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
		goto FAIL;

	// Set output to be ASCII armoured
	gpgme_set_armor(ctx, 1);

	// Use GPG
	const char* path = pakfire_get_path(pakfire);
	char* home = pakfire_path_join(path, "etc/pakfire/gnupg");

	// Check if gpg directories exist
	if (pakfire_access(home, NULL, R_OK) != 0) {
		DEBUG("Creating GPG database at %s\n", home);

		int r = pakfire_mkdir(home, S_IRUSR|S_IWUSR|S_IXUSR);
		if (r) {
			ERROR("Could not initialize the GPG database at %s\n", home);
			goto FAIL;
		}
	}

	// Setup engine
	error = gpgme_ctx_set_engine_info(ctx, GPGME_PROTOCOL_OpenPGP, NULL, home);
	pakfire_free(home);
	if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
		goto FAIL;

	gpgme_engine_info_t engine_info = gpgme_ctx_get_engine_info(ctx);
	DEBUG("GPGME engine info: %s, home = %s\n",
		engine_info->file_name, engine_info->home_dir);

	return ctx;

FAIL:
	gpgme_release(ctx);

	error_string = gpgme_strerror(error);
	ERROR("%s\n", error_string);

	return NULL;
}

static size_t pakfire_count_keys(Pakfire pakfire) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);

	size_t count = 0;

	gpgme_key_t key = NULL;
	gpgme_error_t error = gpgme_op_keylist_start(gpgctx, NULL, 0);
	while (!error) {
		error = gpgme_op_keylist_next(gpgctx, &key);
		if (error)
			break;

		count++;

		gpgme_key_release(key);
	}

	DEBUG("%zu key(s) in keystore\n", count);
	gpgme_release(gpgctx);

	return count;
}

PakfireKey* pakfire_key_list(Pakfire pakfire) {
	size_t count = pakfire_count_keys(pakfire);
	if (count == 0)
		return NULL;

	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);

	PakfireKey* first = pakfire_calloc(count + 1, sizeof(PakfireKey));
	PakfireKey* list = first;

	gpgme_key_t gpgkey = NULL;
	gpgme_error_t error = gpgme_op_keylist_start(gpgctx, NULL, 0);
	while (!error) {
		error = gpgme_op_keylist_next(gpgctx, &gpgkey);
		if (error)
			break;

		// Add key to the list
		*list++ = pakfire_key_create(pakfire, gpgkey);

		gpgme_key_release(gpgkey);
	}

	// Last list item must be NULL
	*list = NULL;

	gpgme_release(gpgctx);

	return first;
}

PakfireKey pakfire_key_create(Pakfire pakfire, gpgme_key_t gpgkey) {
	PakfireKey key = pakfire_calloc(1, sizeof(*key));

	if (key) {
		key->nrefs = 1;
		key->pakfire = pakfire_ref(pakfire);

		key->gpgkey = gpgkey;
		gpgme_key_ref(key->gpgkey);
	}

	return key;
}

static void pakfire_key_free(PakfireKey key) {
	pakfire_unref(key->pakfire);
	gpgme_key_unref(key->gpgkey);

	pakfire_free(key);
}

PakfireKey pakfire_key_ref(PakfireKey key) {
	++key->nrefs;

	return key;
}

void pakfire_key_unref(PakfireKey key) {
	if (--key->nrefs > 0)
		return;

	pakfire_key_free(key);
}

static PakfireKey __pakfire_get_key(Pakfire pakfire, gpgme_ctx_t gpgctx, const char* fingerprint) {
	DEBUG("Seaching for key with fingerprint %s\n", fingerprint);

	PakfireKey key = NULL;
	gpgme_key_t gpgkey = NULL;

	gpgme_error_t error = gpgme_get_key(gpgctx, fingerprint, &gpgkey, 0);
	switch (gpg_error(error)) {
		case GPG_ERR_NO_ERROR:
			key = pakfire_key_create(pakfire, gpgkey);
			gpgme_key_unref(gpgkey);
			break;

		case GPG_ERR_EOF:
			DEBUG("Nothing found\n");
			break;

		default:
			DEBUG("Could not find key: %s\n", gpgme_strerror(error));
			break;
	}

	return key;
}


PakfireKey pakfire_key_get(Pakfire pakfire, const char* fingerprint) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);

	PakfireKey key = __pakfire_get_key(pakfire, gpgctx, fingerprint);
	gpgme_release(gpgctx);

	return key;
}

int pakfire_key_delete(PakfireKey key) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(key->pakfire);

	int r = 0;
	gpgme_error_t error = gpgme_op_delete(gpgctx, key->gpgkey, 1);
	if (error != GPG_ERR_NO_ERROR)
		r = 1;

	gpgme_release(gpgctx);

	return r;
}

const char* pakfire_key_get_fingerprint(PakfireKey key) {
	return key->gpgkey->fpr;
}

const char* pakfire_key_get_uid(PakfireKey key) {
	return key->gpgkey->uids->uid;
}

const char* pakfire_key_get_name(PakfireKey key) {
	return key->gpgkey->uids->name;
}

const char* pakfire_key_get_email(PakfireKey key) {
	return key->gpgkey->uids->email;
}

const char* pakfire_key_get_pubkey_algo(PakfireKey key) {
	switch (key->gpgkey->subkeys->pubkey_algo) {
		case GPGME_PK_RSA:
		case GPGME_PK_RSA_E:
		case GPGME_PK_RSA_S:
			return "RSA";

		case GPGME_PK_DSA:
			return "DSA";

		case GPGME_PK_ECDSA:
			return "ECDSA";

		case GPGME_PK_ECDH:
			return "ECDH";

		case GPGME_PK_ECC:
			return "ECC";

		case GPGME_PK_EDDSA:
			return "EDDSA";

		case GPGME_PK_ELG:
		case GPGME_PK_ELG_E:
			return "ELG";
	}

	return NULL;
}

size_t pakfire_key_get_pubkey_length(PakfireKey key) {
	return key->gpgkey->subkeys->length;
}

time_t pakfire_key_get_created(PakfireKey key) {
	return key->gpgkey->subkeys->timestamp;
}

time_t pakfire_key_get_expires(PakfireKey key) {
	return key->gpgkey->subkeys->expires;
}

int pakfire_key_is_revoked(PakfireKey key) {
	return key->gpgkey->subkeys->revoked;
}

PakfireKey pakfire_key_generate(Pakfire pakfire, const char* userid) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);

	unsigned int flags = 0;

	// Key should be able to be used to sign
	flags |= GPGME_CREATE_SIGN;

	// Don't set a password
	flags |= GPGME_CREATE_NOPASSWD;

	// The key should never expire
	flags |= GPGME_CREATE_NOEXPIRE;

	// Generate the key
	gpgme_error_t error = gpgme_op_createkey(gpgctx, userid,
		DEFAULT_KEY_SIZE, 0, 0, NULL, flags);

	if (error != GPG_ERR_NO_ERROR) {
		printf("ERROR: %s\n", gpgme_strerror(error));
		return NULL;
	}

	// Retrieve the result
	gpgme_genkey_result_t result = gpgme_op_genkey_result(gpgctx);
	gpgme_release(gpgctx);

	// Retrieve the key by its fingerprint
	return pakfire_key_get(pakfire, result->fpr);
}

char* pakfire_key_export(PakfireKey key, pakfire_key_export_mode_t mode) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(key->pakfire);

	gpgme_export_mode_t gpgmode = 0;
	switch (mode) {
		case PAKFIRE_KEY_EXPORT_MODE_SECRET:
			gpgmode |= GPGME_EXPORT_MODE_SECRET;
			break;
	
		default:
			break;
	}

	const char* fingerprint = pakfire_key_get_fingerprint(key);

	// Initialize the buffer
	gpgme_data_t keydata;
	gpgme_error_t error = gpgme_data_new(&keydata);
	if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
		goto FAIL;

	// Encode output as ASCII
	error = gpgme_data_set_encoding(keydata, GPGME_DATA_ENCODING_ARMOR);
	if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
		goto FAIL;

	// Copy the key to the buffer
	error = gpgme_op_export(gpgctx, fingerprint, gpgmode, keydata);
	if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
		goto FAIL;

	// Export key in ASCII format
	size_t length;
	char* mem = gpgme_data_release_and_get_mem(keydata, &length);
	gpgme_release(gpgctx);

	// Copy to our own string buffer
	char* buffer = pakfire_strdup(mem);

	// Release the exported key
	gpgme_free(mem);

	return buffer;

FAIL:
	gpgme_data_release(keydata);
	gpgme_release(gpgctx);

	return NULL;
}

PakfireKey* pakfire_key_import(Pakfire pakfire, const char* data) {
	gpgme_error_t error;
	gpgme_data_t keydata;

	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);

	// Form a data object out of the input without copying data
	error = gpgme_data_new_from_mem(&keydata, data, strlen(data), 0);
	if (error != GPG_ERR_NO_ERROR)
		goto FAIL;

	// Try importing the key(s)
	error = gpgme_op_import(gpgctx, keydata);

	gpgme_import_result_t result;
	switch (error) {
		// Everything went fine
		case GPG_ERR_NO_ERROR:
			result = gpgme_op_import_result(gpgctx);

			DEBUG("Keys considered   = %d\n", result->considered);
			DEBUG("Keys imported     = %d\n", result->imported);
			DEBUG("Keys not imported = %d\n", result->not_imported);

			// Did we import any keys?
			gpgme_import_status_t status = result->imports;
			if (!status)
				return NULL;

			PakfireKey* head = pakfire_calloc(result->imported + 1, sizeof(*head));
			PakfireKey* list = head;

			// Retrieve all imported keys
			while (status) {
				PakfireKey key = __pakfire_get_key(pakfire, gpgctx, status->fpr);
				if (key) {
					const char* fingerprint = pakfire_key_get_fingerprint(key);
					INFO("Imported key %s\n", fingerprint);

					// Append key to list
					*list++ = key;
				}

				status = status->next;
			}

			// Terminate list
			*list = NULL;

			gpgme_data_release(keydata);
			gpgme_release(gpgctx);

			return head;

		// Input was invalid
		case GPG_ERR_INV_VALUE:
			pakfire_errno = PAKFIRE_E_INVALID_INPUT;
			break;

		// Fall through for any other errors
		default:
			ERROR("Failed with gpgme error: %s\n", gpgme_strerror(error));
			break;
	}

FAIL:
	gpgme_data_release(keydata);
	gpgme_release(gpgctx);

	return NULL;
}

char* pakfire_key_dump(PakfireKey key) {
	char* s = "";

	time_t created = pakfire_key_get_created(key);
	char* date_created = pakfire_format_date(created);

	asprintf(&s, "pub %s%zu/%s %s",
		pakfire_key_get_pubkey_algo(key),
		pakfire_key_get_pubkey_length(key),
		pakfire_key_get_fingerprint(key),
		date_created
	);
	pakfire_free(date_created);

	const char* uid = pakfire_key_get_uid(key);
	if (uid) {
		asprintf(&s, "%s\n    %s", s, uid);
	}

	time_t expires = pakfire_key_get_expires(key);
	if (expires) {
			char* date_expires = pakfire_format_date(expires);
			asprintf(&s, "%s\n    %s: %s", s, _("Expires"), date_expires);
			pakfire_free(date_expires);
	}

	return s;
}
