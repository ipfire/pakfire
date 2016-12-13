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

#include <solv/queue.h>
#include <solv/solver.h>
#include <solv/transaction.h>

#ifdef DEBUG
# include <solv/solverdebug.h>
#endif

#include <pakfire/package.h>
#include <pakfire/request.h>
#include <pakfire/selector.h>
#include <pakfire/transaction.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PakfireRequest pakfire_request_create(PakfirePool pool) {
	PakfireRequest request = pakfire_calloc(1, sizeof(*request));
	request->pool = pool;

	queue_init(&request->queue);

	return request;
}

void pakfire_request_free(PakfireRequest request) {
	if (request->transaction)
		transaction_free(request->transaction);

	if (request->solver)
		solver_free(request->solver);

	queue_free(&request->queue);

	pakfire_free(request);
}

PakfirePool pakfire_request_pool(PakfireRequest request) {
	return request->pool;
}

static void init_solver(PakfireRequest request, int flags) {
	PakfirePool pool = pakfire_request_pool(request);

	Solver* solver = solver_create(pool->pool);

	/* Free older solver */
	if (request->solver) {
		solver_free(request->solver);
		request->solver = NULL;
	}

	request->solver = solver;

	if (flags & PAKFIRE_SOLVER_ALLOW_UNINSTALL)
		solver_set_flag(solver, SOLVER_FLAG_ALLOW_UNINSTALL, 1);

	/* no vendor locking */
	solver_set_flag(solver, SOLVER_FLAG_ALLOW_VENDORCHANGE, 1);

	/* no arch change for forcebest */
	solver_set_flag(solver, SOLVER_FLAG_BEST_OBEY_POLICY, 1);
}

static int solve(PakfireRequest request, Queue* queue) {
	/* Remove any previous transactions */
	if (request->transaction) {
		transaction_free(request->transaction);
		request->transaction = NULL;
	}

	pakfire_pool_make_provides_ready(request->pool);

	if (solver_solve(request->solver, queue)) {
#ifdef DEBUG
		solver_printallsolutions(request->solver);
#endif

		return 1;
	}

	/* If the solving process was successful, we get the transaction
	 * from the solver. */
	request->transaction = solver_create_transaction(request->solver);
	transaction_order(request->transaction, 0);

	return 0;
}

int pakfire_request_solve(PakfireRequest request, int flags) {
	init_solver(request, flags);

	Queue queue;
	queue_init_clone(&queue, &request->queue);

	/* Apply forcebest */
	if (flags & PAKFIRE_SOLVER_FORCE_BEST) {
		for (int i = 0; i < queue.count; i += 2) {
			queue.elements[i] |= SOLVER_FORCEBEST;
		}
	}

	/* turn off implicit obsoletes for installonly packages */
	PakfirePool pool = request->pool;
	for (int i = 0; i < pool->installonly.count; i++)
		queue_push2(&queue, SOLVER_MULTIVERSION|SOLVER_SOLVABLE_PROVIDES,
			pool->installonly.elements[i]);

	// XXX EXCLUDES

	int ret = solve(request, &queue);

	queue_free(&queue);

	return ret;
}

PakfireTransaction pakfire_request_get_transaction(PakfireRequest request) {
	if (!request->transaction)
		return NULL;

	return pakfire_transaction_create(request->pool, request->transaction);
}

int pakfire_request_install(PakfireRequest request, PakfirePackage package) {
	queue_push2(&request->queue, SOLVER_SOLVABLE|SOLVER_INSTALL, pakfire_package_id(package));

	return 0;
}

int pakfire_request_install_relation(PakfireRequest request, PakfireRelation relation) {
	return pakfire_relation2queue(relation, &request->queue, SOLVER_INSTALL);
}

int pakfire_request_install_selector(PakfireRequest request, PakfireSelector selector) {
	return pakfire_selector2queue(selector, &request->queue, SOLVER_INSTALL);
}

static int erase_flags(int flags) {
	int additional = 0;

	if (flags & PAKFIRE_CLEAN_DEPS)
		additional |= SOLVER_CLEANDEPS;

	return additional;
}

int pakfire_request_erase(PakfireRequest request, PakfirePackage package, int flags) {
	int additional = erase_flags(flags);
	queue_push2(&request->queue, SOLVER_SOLVABLE|SOLVER_ERASE|additional, pakfire_package_id(package));

	return 0;
}

int pakfire_request_erase_relation(PakfireRequest request, PakfireRelation relation, int flags) {
	int additional = erase_flags(flags);

	return pakfire_relation2queue(relation, &request->queue, SOLVER_ERASE|additional);
}

int pakfire_request_erase_selector(PakfireRequest request, PakfireSelector selector, int flags) {
	int additional = erase_flags(flags);

	return pakfire_selector2queue(selector, &request->queue, SOLVER_ERASE|additional);
}

int pakfire_request_upgrade(PakfireRequest request, PakfirePackage package) {
	return pakfire_request_install(request, package);
}

int pakfire_request_upgrade_relation(PakfireRequest request, PakfireRelation relation) {
	return pakfire_relation2queue(relation, &request->queue, SOLVER_UPDATE);
}

int pakfire_request_upgrade_selector(PakfireRequest request, PakfireSelector selector) {
	return pakfire_selector2queue(selector, &request->queue, SOLVER_UPDATE);
}

int pakfire_request_upgrade_all(PakfireRequest request) {
	queue_push2(&request->queue, SOLVER_UPDATE|SOLVER_SOLVABLE_ALL, 0);

	return 0;
}

int pakfire_request_distupgrade(PakfireRequest request) {
	queue_push2(&request->queue, SOLVER_DISTUPGRADE|SOLVER_SOLVABLE_ALL, 0);

	return 0;
}

int pakfire_request_lock(PakfireRequest request, PakfirePackage package) {
	queue_push2(&request->queue, SOLVER_SOLVABLE|SOLVER_LOCK, pakfire_package_id(package));

	return 0;
}

int pakfire_request_lock_relation(PakfireRequest request, PakfireRelation relation) {
	return pakfire_relation2queue(relation, &request->queue, SOLVER_LOCK);
}

int pakfire_request_lock_selector(PakfireRequest request, PakfireSelector selector) {
	return pakfire_selector2queue(selector, &request->queue, SOLVER_LOCK);
}

int pakfire_request_verify(PakfireRequest request) {
	queue_push2(&request->queue, SOLVER_VERIFY|SOLVER_SOLVABLE_ALL, 0);

	return 0;
}
