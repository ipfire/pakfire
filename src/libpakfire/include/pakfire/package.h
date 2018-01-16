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

#ifndef PAKFIRE_PACKAGE_H
#define PAKFIRE_PACKAGE_H

#include <solv/pooltypes.h>

#include <pakfire/relation.h>
#include <pakfire/relationlist.h>
#include <pakfire/types.h>

PakfirePackage pakfire_package_create(Pakfire pakfire, Id id);
PakfirePackage pakfire_package_create2(Pakfire pakfire, PakfireRepo repo, const char* name, const char* evr, const char* arch);

PakfirePackage pakfire_package_ref(PakfirePackage pkg);
PakfirePackage pakfire_package_unref(PakfirePackage pkg);

int pakfire_package_identical(PakfirePackage pkg1, PakfirePackage pkg2);
int pakfire_package_cmp(PakfirePackage pkg1, PakfirePackage pkg2);
int pakfire_package_evr_cmp(PakfirePackage pkg1, PakfirePackage pkg2);

Id pakfire_package_id(PakfirePackage pkg);

char* pakfire_package_get_nevra(PakfirePackage pkg);
const char* pakfire_package_get_name(PakfirePackage pkg);
void pakfire_package_set_name(PakfirePackage pkg, const char* name);
const char* pakfire_package_get_evr(PakfirePackage pkg);
void pakfire_package_set_evr(PakfirePackage pkg, const char* evr);
unsigned long pakfire_package_get_epoch(PakfirePackage pkg);
const char* pakfire_package_get_version(PakfirePackage pkg);
const char* pakfire_package_get_release(PakfirePackage pkg);
const char* pakfire_package_get_arch(PakfirePackage pkg);
void pakfire_package_set_arch(PakfirePackage pkg, const char* arch);

const char* pakfire_package_get_uuid(PakfirePackage pkg);
void pakfire_package_set_uuid(PakfirePackage pkg, const char* uuid);
const char* pakfire_package_get_checksum(PakfirePackage pkg);
void pakfire_package_set_checksum(PakfirePackage pkg, const char* checksum);
const char* pakfire_package_get_summary(PakfirePackage pkg);
void pakfire_package_set_summary(PakfirePackage pkg, const char* summary);
const char* pakfire_package_get_description(PakfirePackage pkg);
void pakfire_package_set_description(PakfirePackage pkg, const char* description);
const char* pakfire_package_get_license(PakfirePackage pkg);
void pakfire_package_set_license(PakfirePackage pkg, const char* license);
const char* pakfire_package_get_url(PakfirePackage pkg);
void pakfire_package_set_url(PakfirePackage pkg, const char* url);
const char** pakfire_package_get_groups(PakfirePackage pkg);
void pakfire_package_set_groups(PakfirePackage pkg, const char** grouplist);
const char* pakfire_package_get_vendor(PakfirePackage pkg);
void pakfire_package_set_vendor(PakfirePackage pkg, const char* vendor);
const char* pakfire_package_get_maintainer(PakfirePackage pkg);
void pakfire_package_set_maintainer(PakfirePackage pkg, const char* maintainer);
const char* pakfire_package_get_filename(PakfirePackage pkg);
void pakfire_package_set_filename(PakfirePackage pkg, const char* filename);
int pakfire_package_is_installed(PakfirePackage pkg);
unsigned long long pakfire_package_get_downloadsize(PakfirePackage pkg);
void pakfire_package_set_downloadsize(PakfirePackage pkg, unsigned long long downloadsize);
unsigned long long pakfire_package_get_installsize(PakfirePackage pkg);
void pakfire_package_set_installsize(PakfirePackage pkg, unsigned long long installsize);
unsigned long long pakfire_package_get_size(PakfirePackage pkg);
const char* pakfire_package_get_buildhost(PakfirePackage pkg);
void pakfire_package_set_buildhost(PakfirePackage pkg, const char* buildhost);
unsigned long long pakfire_package_get_buildtime(PakfirePackage pkg);
void pakfire_package_set_buildtime(PakfirePackage pkg, unsigned long long buildtime);
unsigned long long pakfire_package_get_installtime(PakfirePackage pkg);

PakfireRelationList pakfire_package_get_provides(PakfirePackage pkg);
void pakfire_package_set_provides(PakfirePackage pkg, PakfireRelationList relationlist);
void pakfire_package_add_provides(PakfirePackage pkg, PakfireRelation relation);
PakfireRelationList pakfire_package_get_requires(PakfirePackage pkg);
void pakfire_package_set_requires(PakfirePackage pkg, PakfireRelationList relationlist);
void pakfire_package_add_requires(PakfirePackage pkg, PakfireRelation relation);
PakfireRelationList pakfire_package_get_conflicts(PakfirePackage pkg);
void pakfire_package_set_conflicts(PakfirePackage pkg, PakfireRelationList relationlist);
void pakfire_package_add_conflicts(PakfirePackage pkg, PakfireRelation relation);
PakfireRelationList pakfire_package_get_obsoletes(PakfirePackage pkg);
void pakfire_package_set_obsoletes(PakfirePackage pkg, PakfireRelationList relationlist);
void pakfire_package_add_obsoletes(PakfirePackage pkg, PakfireRelation relation);
PakfireRelationList pakfire_package_get_recommends(PakfirePackage pkg);
void pakfire_package_set_recommends(PakfirePackage pkg, PakfireRelationList relationlist);
void pakfire_package_add_recommends(PakfirePackage pkg, PakfireRelation relation);
PakfireRelationList pakfire_package_get_suggests(PakfirePackage pkg);
void pakfire_package_set_suggests(PakfirePackage pkg, PakfireRelationList relationlist);
void pakfire_package_add_suggests(PakfirePackage pkg, PakfireRelation relation);

PakfireRepo pakfire_package_get_repo(PakfirePackage pkg);
void pakfire_package_set_repo(PakfirePackage pkg, PakfireRepo repo);

char* pakfire_package_get_location(PakfirePackage pkg);

char* pakfire_package_dump(PakfirePackage pkg, int flags);

int pakfire_package_is_cached(PakfirePackage pkg);
char* pakfire_package_get_cache_path(PakfirePackage pkg);
char* pakfire_package_get_cache_full_path(PakfirePackage pkg);

PakfireFile pakfire_package_get_filelist(PakfirePackage pkg);
PakfireFile pakfire_package_filelist_append(PakfirePackage pkg, const char* filename);
#if 0
PakfireFile pakfire_package_filelist_append(PakfirePackage pkg);
#endif
void pakfire_package_filelist_remove(PakfirePackage pkg);

enum pakfire_package_keynames {
    PAKFIRE_PKG,
    PAKFIRE_PKG_ALL,
    PAKFIRE_PKG_ARCH,
    PAKFIRE_PKG_CONFLICTS,
    PAKFIRE_PKG_DESCRIPTION,
    PAKFIRE_PKG_EPOCH,
    PAKFIRE_PKG_EVR,
    PAKFIRE_PKG_FILE,
    PAKFIRE_PKG_NAME,
    PAKFIRE_PKG_OBSOLETES,
    PAKFIRE_PKG_PROVIDES,
    PAKFIRE_PKG_RELEASE,
    PAKFIRE_PKG_REPONAME,
    PAKFIRE_PKG_REQUIRES,
    PAKFIRE_PKG_SOURCERPM,
    PAKFIRE_PKG_SUMMARY,
    PAKFIRE_PKG_URL,
    PAKFIRE_PKG_VERSION,
    PAKFIRE_PKG_LOCATION
};

enum pakfire_package_dump_flags {
	PAKFIRE_PKG_DUMP_FILELIST = 1 << 0,
	PAKFIRE_PKG_DUMP_LONG     = 1 << 1,
};

#endif /* PAKFIRE_PACKAGE_H */
