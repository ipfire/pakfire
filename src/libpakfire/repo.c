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

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <solv/repo.h>
#include <solv/repo_solv.h>
#include <solv/repo_write.h>

#include <lzma.h>

#include <pakfire/constants.h>
#include <pakfire/errno.h>
#include <pakfire/package.h>
#include <pakfire/pool.h>
#include <pakfire/private.h>
#include <pakfire/repo.h>
#include <pakfire/repocache.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

const uint8_t XZ_HEADER_MAGIC[] = { 0xFD, '7', 'z', 'X', 'Z', 0x00 };
const size_t XZ_HEADER_LENGTH = sizeof(XZ_HEADER_MAGIC);

static Repo* get_repo_by_name(Pool* pool, const char* name) {
	Repo* repo;
	int i;

	FOR_REPOS(i, repo) {
		if (strcmp(repo->name, name) == 0)
			return repo;
	}

	return NULL;
}

static PakfireRepo get_pakfire_repo_by_name(PakfirePool pool, const char* name) {
	Repo* repo = get_repo_by_name(pool->pool, name);

	if (repo)
		return repo->appdata;

	return NULL;
}

PAKFIRE_EXPORT PakfireRepo pakfire_repo_create(PakfirePool pool, const char* name) {
	PakfireRepo repo = get_pakfire_repo_by_name(pool, name);
	if (repo) {
		repo->nrefs++;
		return repo;
	}

	Repo* r = get_repo_by_name(pool->pool, name);
	if (!r)
		r = repo_create(pool->pool, name);

	return pakfire_repo_create_from_repo(pool, r);
}

PAKFIRE_EXPORT PakfireRepo pakfire_repo_create_from_repo(PakfirePool pool, Repo* r) {
	PakfireRepo repo;

	if (r->appdata) {
		repo = r->appdata;
		repo->nrefs++;

	} else {
		repo = pakfire_calloc(1, sizeof(*repo));
		if (repo) {
			repo->pool = pool;

			repo->repo = r;
			repo->cache = pakfire_repocache_create(repo);
			repo->repo->appdata = repo;

			repo->filelist = repo_add_repodata(r, REPO_EXTEND_SOLVABLES|REPO_LOCALPOOL|REPO_NO_INTERNALIZE|REPO_NO_LOCATION);

			// Initialize reference counter
			repo->nrefs = 1;
		}
	}

	return repo;
}

PAKFIRE_EXPORT void pakfire_repo_free(PakfireRepo repo) {
	if (--repo->nrefs > 0)
		return;

	if (repo->repo)
		repo->repo->appdata = NULL;

	if (repo->cache)
		pakfire_repocache_free(repo->cache);

	pakfire_free(repo);
}

PAKFIRE_EXPORT PakfirePool pakfire_repo_pool(PakfireRepo repo) {
	return repo->pool;
}

PAKFIRE_EXPORT int pakfire_repo_identical(PakfireRepo repo1, PakfireRepo repo2) {
	Repo* r1 = repo1->repo;
	Repo* r2 = repo2->repo;

	return strcmp(r1->name, r2->name);
}

PAKFIRE_EXPORT int pakfire_repo_cmp(PakfireRepo repo1, PakfireRepo repo2) {
	Repo* r1 = repo1->repo;
	Repo* r2 = repo2->repo;

	if (r1->priority > r2->priority)
		return 1;

	else if (r1->priority < r2->priority)
		return -1;

	return strcmp(r1->name, r2->name);
}

PAKFIRE_EXPORT int pakfire_repo_count(PakfireRepo repo) {
	Pool* pool = pakfire_repo_solv_pool(repo);
	int cnt = 0;

	for (int i = 2; i < pool->nsolvables; i++) {
		Solvable* s = pool->solvables + i;
		if (s->repo && s->repo == repo->repo)
			cnt++;
	}

	return cnt;
}

PAKFIRE_EXPORT void pakfire_repo_internalize(PakfireRepo repo) {
	repo_internalize(repo->repo);
}

PAKFIRE_EXPORT const char* pakfire_repo_get_name(PakfireRepo repo) {
	return repo->repo->name;
}

PAKFIRE_EXPORT void pakfire_repo_set_name(PakfireRepo repo, const char* name) {
	repo->repo->name = pakfire_strdup(name);
}

PAKFIRE_EXPORT int pakfire_repo_get_enabled(PakfireRepo repo) {
	return !repo->repo->disabled;
}

PAKFIRE_EXPORT void pakfire_repo_set_enabled(PakfireRepo repo, int enabled) {
	repo->repo->disabled = !enabled;

	PakfirePool pool = pakfire_repo_pool(repo);
	pool->provides_ready = 0;
}

PAKFIRE_EXPORT int pakfire_repo_get_priority(PakfireRepo repo) {
	return repo->repo->priority;
}

PAKFIRE_EXPORT void pakfire_repo_set_priority(PakfireRepo repo, int priority) {
	repo->repo->priority = priority;
}

PAKFIRE_EXPORT int pakfire_repo_is_installed_repo(PakfireRepo repo) {
	PakfirePool pool = pakfire_repo_pool(repo);

	PakfireRepo installed_repo = pakfire_pool_get_installed_repo(pool);

	return pakfire_repo_identical(repo, installed_repo);
}

PAKFIRE_EXPORT int pakfire_repo_read_solv(PakfireRepo repo, const char* filename, int flags) {
	FILE* f = fopen(filename, "rb");
	if (!f) {
		return PAKFIRE_E_IO;
	}

	int ret = pakfire_repo_read_solv_fp(repo, f, flags);
	fclose(f);

	return ret;
}

struct xz_cookie {
	FILE* f;
	lzma_stream stream;
	int done;

	// XXX This should actually be larger than one byte, but fread()
	// in _xz_read() somehow segfaults when this is larger
	uint8_t buffer[1];
};

static ssize_t _xz_read(void* data, char* buffer, size_t size) {
	struct xz_cookie* cookie = (struct xz_cookie*)data;
	if (!cookie)
		return -1;

	// Return nothing after we are done
	if (cookie->done)
		return 0;

	lzma_action action = LZMA_RUN;

	// Set output to allocated buffer
	cookie->stream.next_out  = (uint8_t *)buffer;
	cookie->stream.avail_out = size;

	while (1) {
		// Read something when the input buffer is empty
		if (cookie->stream.avail_in == 0) {
			cookie->stream.next_in  = cookie->buffer;
			cookie->stream.avail_in = fread(cookie->buffer,
				1, sizeof(cookie->buffer), cookie->f);

			// Break if the input file could not be read
			if (ferror(cookie->f))
				return -1;

			// Finish after we have reached the end of the input file
			if (feof(cookie->f)) {
				action = LZMA_FINISH;
				cookie->done = 1;
			}
		}

		lzma_ret ret = lzma_code(&cookie->stream, action);

		// If the stream has ended, we just send the
		// remaining output and mark that we are done.
		if (ret == LZMA_STREAM_END) {
			cookie->done = 1;
			return size - cookie->stream.avail_out;
		}

		// Break on all other unexpected errors
		if (ret != LZMA_OK)
			return -1;

		// When we have read enough to fill the entire output buffer, we return
		if (cookie->stream.avail_out == 0)
			return size;

		if (cookie->done)
			return -1;
	}
}

static int _xz_close(void* data) {
	struct xz_cookie* cookie = (struct xz_cookie*)data;

	// Free the deocder
	lzma_end(&cookie->stream);

	// Close input file
	fclose(cookie->f);

	return 0;
}

static FILE* decompression_proxy(FILE* f) {
	uint8_t buffer;

	// Search for XZ header
	for (unsigned int i = 0; i < XZ_HEADER_LENGTH; i++) {
		fread(&buffer, 1, 1, f);

		if (buffer != XZ_HEADER_MAGIC[i])
			goto UNCOMPRESSED;
	}

	// Reset to beginning
	fseek(f, 0, SEEK_SET);

	// If we get here, an XZ header was found
	struct xz_cookie cookie = {
		.f = f,
		.stream = LZMA_STREAM_INIT,
		.done = 0,
	};

	// Initialise the decoder
	lzma_ret ret = lzma_stream_decoder(&cookie.stream, UINT64_MAX, 0);
	if (ret != LZMA_OK)
		return NULL;

	cookie_io_functions_t functions = {
		.read  = _xz_read,
		.write = NULL,
		.seek  = NULL,
		.close = _xz_close,
	};

	return fopencookie(&cookie, "rb", functions);

UNCOMPRESSED:
	fseek(f, 0, SEEK_SET);
	return f;
}

PAKFIRE_EXPORT int pakfire_repo_read_solv_fp(PakfireRepo repo, FILE *f, int flags) {
	f = decompression_proxy(f);

	int ret = repo_add_solv(repo->repo, f, flags);

	switch (ret) {
		// Everything OK
		case 0:
			break;

		// Not SOLV format
		case 1:
			return PAKFIRE_E_SOLV_NOT_SOLV;

		// Unsupported version
		case 2:
			return PAKFIRE_E_SOLV_UNSUPPORTED;

		// End of file
		case 3:
			return PAKFIRE_E_EOF;

		// Corrupted
		case 4:
		case 5:
		case 6:
		default:
			return PAKFIRE_E_SOLV_CORRUPTED;
	}

	repo->pool->provides_ready = 0;

	return ret;
}

PAKFIRE_EXPORT int pakfire_repo_write_solv(PakfireRepo repo, const char* filename, int flags) {
	FILE* f = fopen(filename, "wb");
	if (!f) {
		return PAKFIRE_E_IO;
	}

	int ret = pakfire_repo_write_solv_fp(repo, f, flags);
	fclose(f);

	return ret;
}

PAKFIRE_EXPORT int pakfire_repo_write_solv_fp(PakfireRepo repo, FILE *f, int flags) {
	pakfire_repo_internalize(repo);

	return repo_write(repo->repo, f);
}

PAKFIRE_EXPORT PakfirePackage pakfire_repo_add_package(PakfireRepo repo) {
	Id id = repo_add_solvable(repo->repo);

	return pakfire_package_create(repo->pool, id);
}

PAKFIRE_EXPORT PakfireRepoCache pakfire_repo_get_cache(PakfireRepo repo) {
	assert(repo);

	return repo->cache;
}

PAKFIRE_EXPORT int pakfire_repo_clean(PakfireRepo repo) {
	PakfireRepoCache cache = pakfire_repo_get_cache(repo);

	if (cache)
		return pakfire_repocache_destroy(cache);

	return 0;
}
