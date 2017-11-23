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

#include <pakfire/key.h>
#include <pakfire/pakfire.h>
#include <pakfire/util.h>

static gpgme_ctx_t pakfire_get_gpgctx(Pakfire pakfire) {
	static int gpg_initialized = 0;
	gpgme_error_t error;
	const char* error_string;

	if (!gpg_initialized) {
		// Initialise gpgme
		const char* version = gpgme_check_version(NULL);
		assert(version);
#if 0
		printf("version = %s\n", version);
#endif

		// Check if we support GPG
		error = gpgme_engine_check_version(GPGME_PROTOCOL_OpenPGP);
		if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
			goto FAIL;

		// Use GPG
		char* home = pakfire_path_join(pakfire->path, "/etc/pakfire/gnupg");
		error = gpgme_set_engine_info(GPGME_PROTOCOL_OpenPGP, NULL, home);
		pakfire_free(home);
		if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
			goto FAIL;

		gpgme_engine_info_t engine_info;
		error = gpgme_get_engine_info(&engine_info);
		if (gpg_err_code(error) != GPG_ERR_NO_ERROR)
			goto FAIL;

#if 0
		printf("GPGME engine info: %s, %s\n",
			engine_info->file_name, engine_info->home_dir);
#endif

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

	return ctx;

FAIL:
	error_string = gpgme_strerror(error);
	printf("ERROR: %s\n", error_string);

	return NULL;
}

PakfireKey* pakfire_key_list(Pakfire pakfire) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);
	assert(gpgctx);

	PakfireKey* first = pakfire_calloc(1, sizeof(PakfireKey));
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

	return first;
}

PakfireKey pakfire_key_create(Pakfire pakfire, gpgme_key_t gpgkey) {
	PakfireKey key = pakfire_calloc(1, sizeof(*key));

	if (key) {
		key->pakfire = pakfire_ref(pakfire);

		key->gpgkey = gpgkey;
		gpgme_key_ref(key->gpgkey);
	}

	return key;
}

void pakfire_key_free(PakfireKey key) {
	pakfire_unref(key->pakfire);
	gpgme_key_unref(key->gpgkey);

	pakfire_free(key);
}

PakfireKey pakfire_key_get(Pakfire pakfire, const char* fingerprint) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);
	assert(gpgctx);

	gpgme_key_t gpgkey = NULL;
	gpgme_error_t error = gpgme_get_key(gpgctx, fingerprint, &gpgkey, 1);
	if (error != GPG_ERR_NO_ERROR)
		return NULL;

	PakfireKey key = pakfire_key_create(pakfire, gpgkey);
	gpgme_key_unref(gpgkey);
	gpgme_release(gpgctx);

	return key;
}

const char* pakfire_key_get_fingerprint(PakfireKey key) {
	return key->gpgkey->fpr;
}

PakfireKey pakfire_key_generate(Pakfire pakfire, const char* userid) {
	gpgme_ctx_t gpgctx = pakfire_get_gpgctx(pakfire);
	assert(gpgctx);

	unsigned int flags = 0;

	// Key should be able to be used to sign
	flags |= GPGME_CREATE_SIGN;

	// Don't set a password
	flags |= GPGME_CREATE_NOPASSWD;

	// The key should never expire
	flags |= GPGME_CREATE_NOEXPIRE;

	// Generate the key
	gpgme_error_t error = gpgme_op_createkey(gpgctx, userid,
		"rsa512", 0, 0, NULL, flags);

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
	assert(gpgctx);

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
