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

#ifndef PAKFIRE_REPO_H
#define PAKFIRE_REPO_H

#include <time.h>
#include <unistd.h>

#include <pakfire/types.h>

PakfireRepo pakfire_repo_create(Pakfire pakfire, const char* name);

PakfireRepo pakfire_repo_ref(PakfireRepo repo);
PakfireRepo pakfire_repo_unref(PakfireRepo repo);
Pakfire pakfire_repo_get_pakfire(PakfireRepo repo);

int pakfire_repo_identical(PakfireRepo repo1, PakfireRepo repo2);
int pakfire_repo_cmp(PakfireRepo repo1, PakfireRepo repo2);
int pakfire_repo_count(PakfireRepo repo);

void pakfire_repo_internalize(PakfireRepo repo);

const char* pakfire_repo_get_name(PakfireRepo repo);
void pakfire_repo_set_name(PakfireRepo repo, const char* name);

int pakfire_repo_get_enabled(PakfireRepo repo);
void pakfire_repo_set_enabled(PakfireRepo repo, int enabled);

int pakfire_repo_get_priority(PakfireRepo repo);
void pakfire_repo_set_priority(PakfireRepo repo, int priority);

const char* pakfire_repo_get_baseurl(PakfireRepo repo);
int pakfire_repo_set_baseurl(PakfireRepo repo, const char* baseurl);

const char* pakfire_repo_get_keyfile(PakfireRepo repo);
int pakfire_repo_set_keyfile(PakfireRepo repo, const char* keyfile);

const char* pakfire_repo_get_mirrorlist(PakfireRepo repo);
int pakfire_repo_set_mirrorlist(PakfireRepo repo, const char* mirrorlist);

int pakfire_repo_is_installed_repo(PakfireRepo repo);

int pakfire_repo_read_solv(PakfireRepo repo, const char* filename, int flags);
int pakfire_repo_read_solv_fp(PakfireRepo repo, FILE *f, int flags);

int pakfire_repo_write_solv(PakfireRepo repo, const char* filename, int flags);
int pakfire_repo_write_solv_fp(PakfireRepo repo, FILE *f, int flags);

// Cache

int pakfire_repo_clean(PakfireRepo repo);
char* pakfire_repo_cache_get_path(PakfireRepo repo, const char* path);
FILE* pakfire_repo_cache_open(PakfireRepo repo, const char* path, const char* mode);
int pakfire_repo_cache_access(PakfireRepo repo, const char* path, int mode);
time_t pakfire_repo_cache_age(PakfireRepo repo, const char* path);

#ifdef PAKFIRE_PRIVATE

#include <solv/repo.h>

PakfireRepo pakfire_repo_create_from_repo(Pakfire pakfire, Repo* r);
void pakfire_repo_free_all(Pakfire pakfire);

PakfirePackage pakfire_repo_add_package(PakfireRepo repo);

Repo* pakfire_repo_get_repo(PakfireRepo repo);
Repodata* pakfire_repo_get_repodata(PakfireRepo repo);

#endif

#endif /* PAKFIRE_REPO_H */
