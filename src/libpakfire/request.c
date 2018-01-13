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

#include <pakfire/logging.h>
#include <pakfire/package.h>
#include <pakfire/private.h>
#include <pakfire/problem.h>
#include <pakfire/request.h>
#include <pakfire/selector.h>
#include <pakfire/transaction.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PAKFIRE_EXPORT PakfireRequest pakfire_request_create(PakfirePool pool) {
	PakfireRequest request = pakfire_calloc(1, sizeof(*request));
	request->pool = pool;

	queue_init(&request->queue);

	// Initialise reference counter
	request->nrefs = 1;

	return request;
}

PAKFIRE_EXPORT PakfireRequest pakfire_request_ref(PakfireRequest request) {
	request->nrefs++;

	return request;
}

PAKFIRE_EXPORT void pakfire_request_free(PakfireRequest request) {
	if (--request->nrefs > 0)
		return;

	if (request->transaction)
		transaction_free(request->transaction);

	if (request->solver)
		solver_free(request->solver);

	queue_free(&request->queue);

	pakfire_free(request);
}

PAKFIRE_EXPORT PakfirePool pakfire_request_pool(PakfireRequest request) {
	return request->pool;
}

static void init_solver(PakfireRequest request, int flags) {
	PakfirePool pool = pakfire_request_pool(request);
	Pool* p = pakfire_pool_get_solv_pool(pool);

	Solver* solver = solver_create(p);

	/* Free older solver */
	if (request->solver) {
		solver_free(request->solver);
		request->solver = NULL;
	}

	request->solver = solver;

	if (flags & PAKFIRE_SOLVER_ALLOW_ARCHCHANGE)
		solver_set_flag(solver, SOLVER_FLAG_ALLOW_ARCHCHANGE, 1);

	if (flags & PAKFIRE_SOLVER_ALLOW_DOWNGRADE)
		solver_set_flag(solver, SOLVER_FLAG_ALLOW_DOWNGRADE, 1);

	if (flags & PAKFIRE_SOLVER_ALLOW_UNINSTALL)
		solver_set_flag(solver, SOLVER_FLAG_ALLOW_UNINSTALL, 1);

	if (flags & PAKFIRE_SOLVER_ALLOW_VENDORCHANGE)
		solver_set_flag(solver, SOLVER_FLAG_ALLOW_VENDORCHANGE, 1);

	if (flags & PAKFIRE_SOLVER_WITHOUT_RECOMMENDS)
		solver_set_flag(solver, SOLVER_FLAG_IGNORE_RECOMMENDED, 1);

	/* no arch change for forcebest */
	solver_set_flag(solver, SOLVER_FLAG_BEST_OBEY_POLICY, 1);
}

static int solve(PakfireRequest request, Queue* queue) {
	/* Remove any previous transactions */
	if (request->transaction) {
		transaction_free(request->transaction);
		request->transaction = NULL;
	}

	pakfire_pool_apply_changes(request->pool);

	// Save time when we starting solving
	clock_t solving_start = clock();

	if (solver_solve(request->solver, queue)) {
#ifdef DEBUG
		solver_printallsolutions(request->solver);
#endif

		return 1;
	}

	// Save time when we finished solving
	clock_t solving_end = clock();

	DEBUG("Solved request in %.4fms\n",
		(double)(solving_end - solving_start) * 1000 / CLOCKS_PER_SEC);

	/* If the solving process was successful, we get the transaction
	 * from the solver. */
	request->transaction = solver_create_transaction(request->solver);
	transaction_order(request->transaction, 0);

	return 0;
}

PAKFIRE_EXPORT int pakfire_request_solve(PakfireRequest request, int flags) {
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
	Queue* installonly = pakfire_pool_get_installonly_queue(request->pool);
	for (int i = 0; i < installonly->count; i++)
		queue_push2(&queue, SOLVER_MULTIVERSION|SOLVER_SOLVABLE_PROVIDES,
			installonly->elements[i]);

	// XXX EXCLUDES

	int ret = solve(request, &queue);

	queue_free(&queue);

	return ret;
}

PAKFIRE_EXPORT PakfireProblem pakfire_request_get_problems(PakfireRequest request) {
	Id problem = 0;
	PakfireProblem ret = NULL;

	while ((problem = solver_next_problem(request->solver, problem)) != 0) {
		PakfireProblem p = pakfire_problem_create(request, problem);

		if (ret)
			pakfire_problem_append(ret, p);
		else
			ret = p;
	}

	return ret;
}

PAKFIRE_EXPORT PakfireTransaction pakfire_request_get_transaction(PakfireRequest request) {
	if (!request->transaction)
		return NULL;

	return pakfire_transaction_create(request->pool, request->transaction);
}

PAKFIRE_EXPORT int pakfire_request_install(PakfireRequest request, PakfirePackage package) {
	queue_push2(&request->queue, SOLVER_SOLVABLE|SOLVER_INSTALL, pakfire_package_id(package));

	return 0;
}

PAKFIRE_EXPORT int pakfire_request_install_relation(PakfireRequest request, PakfireRelation relation) {
	return pakfire_relation2queue(relation, &request->queue, SOLVER_INSTALL);
}

PAKFIRE_EXPORT int pakfire_request_install_selector(PakfireRequest request, PakfireSelector selector) {
	return pakfire_selector2queue(selector, &request->queue, SOLVER_INSTALL);
}

static int erase_flags(int flags) {
	int additional = 0;

	if (flags & PAKFIRE_CLEAN_DEPS)
		additional |= SOLVER_CLEANDEPS;

	return additional;
}

PAKFIRE_EXPORT int pakfire_request_erase(PakfireRequest request, PakfirePackage package, int flags) {
	int additional = erase_flags(flags);
	queue_push2(&request->queue, SOLVER_SOLVABLE|SOLVER_ERASE|additional, pakfire_package_id(package));

	return 0;
}

PAKFIRE_EXPORT int pakfire_request_erase_relation(PakfireRequest request, PakfireRelation relation, int flags) {
	int additional = erase_flags(flags);

	return pakfire_relation2queue(relation, &request->queue, SOLVER_ERASE|additional);
}

PAKFIRE_EXPORT int pakfire_request_erase_selector(PakfireRequest request, PakfireSelector selector, int flags) {
	int additional = erase_flags(flags);

	return pakfire_selector2queue(selector, &request->queue, SOLVER_ERASE|additional);
}

PAKFIRE_EXPORT int pakfire_request_upgrade(PakfireRequest request, PakfirePackage package) {
	return pakfire_request_install(request, package);
}

PAKFIRE_EXPORT int pakfire_request_upgrade_relation(PakfireRequest request, PakfireRelation relation) {
	return pakfire_relation2queue(relation, &request->queue, SOLVER_UPDATE);
}

PAKFIRE_EXPORT int pakfire_request_upgrade_selector(PakfireRequest request, PakfireSelector selector) {
	return pakfire_selector2queue(selector, &request->queue, SOLVER_UPDATE);
}

PAKFIRE_EXPORT int pakfire_request_upgrade_all(PakfireRequest request) {
	queue_push2(&request->queue, SOLVER_UPDATE|SOLVER_SOLVABLE_ALL, 0);

	return 0;
}

PAKFIRE_EXPORT int pakfire_request_distupgrade(PakfireRequest request) {
	queue_push2(&request->queue, SOLVER_DISTUPGRADE|SOLVER_SOLVABLE_ALL, 0);

	return 0;
}

PAKFIRE_EXPORT int pakfire_request_lock(PakfireRequest request, PakfirePackage package) {
	queue_push2(&request->queue, SOLVER_SOLVABLE|SOLVER_LOCK, pakfire_package_id(package));

	return 0;
}

PAKFIRE_EXPORT int pakfire_request_lock_relation(PakfireRequest request, PakfireRelation relation) {
	return pakfire_relation2queue(relation, &request->queue, SOLVER_LOCK);
}

PAKFIRE_EXPORT int pakfire_request_lock_selector(PakfireRequest request, PakfireSelector selector) {
	return pakfire_selector2queue(selector, &request->queue, SOLVER_LOCK);
}

PAKFIRE_EXPORT int pakfire_request_verify(PakfireRequest request) {
	queue_push2(&request->queue, SOLVER_VERIFY|SOLVER_SOLVABLE_ALL, 0);

	return 0;
}
