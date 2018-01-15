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

#ifndef PAKFIRE_TYPES_H
#define PAKFIRE_TYPES_H

#include <stdarg.h>

typedef struct _Pakfire* Pakfire;
typedef struct _PakfireArchive* PakfireArchive;
typedef struct _PakfireArchiveSignature* PakfireArchiveSignature;
typedef struct _PakfireCache* PakfireCache;
typedef struct _PakfireFile* PakfireFile;
typedef struct _PakfireFilter* PakfireFilter;
typedef struct _PakfireKey* PakfireKey;
typedef struct _PakfirePackage* PakfirePackage;
typedef struct _PakfirePackageCache* PakfirePackageCache;
typedef struct _PakfirePackageList* PakfirePackageList;
typedef struct _PakfirePool* PakfirePool;
typedef struct _PakfireProblem* PakfireProblem;
typedef struct _PakfireRelation* PakfireRelation;
typedef struct _PakfireRelationList* PakfireRelationList;
typedef struct _PakfireRepo* PakfireRepo;
typedef struct _PakfireRepoCache* PakfireRepoCache;
typedef struct _PakfireRequest* PakfireRequest;
typedef struct _PakfireSelector* PakfireSelector;
typedef struct _PakfireSolution* PakfireSolution;
typedef struct _PakfireStep* PakfireStep;
typedef struct _PakfireTransaction* PakfireTransaction;

typedef void (*pakfire_log_function_t)(int priority,
		const char* file, int line, const char* fn,
		const char* format, va_list args);

enum _pakfire_comparison_types {
	PAKFIRE_ICASE     = 1 << 0,
	PAKFIRE_NOT       = 1 << 1,
	PAKFIRE_NAME_ONLY = 1 << 2,
	PAKFIRE_SUBSTRING = 1 << 3,

	PAKFIRE_EQ        = 1 << 8,
	PAKFIRE_LT        = 1 << 9,
	PAKFIRE_LE        = PAKFIRE_EQ|PAKFIRE_LT,
	PAKFIRE_GT        = 1 << 10,
	PAKFIRE_GE        = PAKFIRE_EQ|PAKFIRE_GT,
	PAKFIRE_NEQ       = PAKFIRE_EQ|PAKFIRE_NOT,

	PAKFIRE_SUBSTR    = 1 << 11,
	PAKFIRE_GLOB      = 1 << 12,
};

typedef enum _pakfire_action_types {
	PAKFIRE_ACTION_NOOP      = 0,
	PAKFIRE_ACTION_VERIFY    = 1 << 0,
	PAKFIRE_ACTION_EXECUTE   = 1 << 1,
	PAKFIRE_ACTION_PRETRANS  = 1 << 2,
	PAKFIRE_ACTION_POSTTRANS = 1 << 3,
} pakfire_action_type_t;

typedef enum _pakfire_step_types {
	PAKFIRE_STEP_IGNORE = 0,
	PAKFIRE_STEP_INSTALL,
	PAKFIRE_STEP_REINSTALL,
	PAKFIRE_STEP_ERASE,
	PAKFIRE_STEP_UPGRADE,
	PAKFIRE_STEP_DOWNGRADE,
	PAKFIRE_STEP_OBSOLETE,
} pakfire_step_type_t;

#define PAKFIRE_SOLVABLE_FILEMARKER "solvable:filemarker"

#endif /* PAKFIRE_TYPES_H */
