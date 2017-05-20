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

#ifndef PAKFIRE_REQUEST_H
#define PAKFIRE_REQUEST_H

#include <solv/queue.h>
#include <solv/solver.h>
#include <solv/transaction.h>

#include <pakfire/types.h>

enum _pakfire_request_op_flags {
	PAKFIRE_CHECK_INSTALLED = 1 << 0,
	PAKFIRE_CLEAN_DEPS      = 1 << 1,
};

enum _pakfire_solver_flags {
	PAKFIRE_SOLVER_ALLOW_UNINSTALL = 1 << 0,
	PAKFIRE_SOLVER_FORCE_BEST      = 1 << 1,
};

PakfireRequest pakfire_request_create(PakfirePool pool);
PakfireRequest pakfire_request_ref(PakfireRequest request);
void pakfire_request_free(PakfireRequest request);

PakfirePool pakfire_request_pool(PakfireRequest request);

int pakfire_request_solve(PakfireRequest request, int flags);
PakfireProblem pakfire_request_get_problems(PakfireRequest request);
PakfireTransaction pakfire_request_get_transaction(PakfireRequest request);

int pakfire_request_install(PakfireRequest request, PakfirePackage package);
int pakfire_request_install_relation(PakfireRequest request, PakfireRelation relation);
int pakfire_request_install_selector(PakfireRequest request, PakfireSelector selector);

int pakfire_request_erase(PakfireRequest request, PakfirePackage package, int flags);
int pakfire_request_erase_relation(PakfireRequest request, PakfireRelation relation, int flags);
int pakfire_request_erase_selector(PakfireRequest request, PakfireSelector selector, int flags);

int pakfire_request_upgrade(PakfireRequest request, PakfirePackage package);
int pakfire_request_upgrade_relation(PakfireRequest request, PakfireRelation relation);
int pakfire_request_upgrade_selector(PakfireRequest request, PakfireSelector selector);

int pakfire_request_upgrade_all(PakfireRequest request);
int pakfire_request_distupgrade(PakfireRequest request);

int pakfire_request_lock(PakfireRequest request, PakfirePackage package);
int pakfire_request_lock_relation(PakfireRequest request, PakfireRelation relation);
int pakfire_request_lock_selector(PakfireRequest request, PakfireSelector selector);

int pakfire_request_verify(PakfireRequest request);

#ifdef PAKFIRE_PRIVATE

struct _PakfireRequest {
	PakfirePool pool;
	Queue queue;
	Solver* solver;
	Transaction* transaction;
	int nrefs;
};

#endif

#endif /* PAKFIRE_REQUEST_H */
