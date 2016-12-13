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

#include <solv/transaction.h>

#include <pakfire/package.h>
#include <pakfire/packagelist.h>
#include <pakfire/step.h>
#include <pakfire/transaction.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

PakfireTransaction pakfire_transaction_create(PakfirePool pool, Transaction* trans) {
	PakfireTransaction transaction = pakfire_calloc(1, sizeof(*transaction));
	transaction->pool = pool;

	// Clone the transaction, so we get independent from what ever called this.
	if (trans) {
		transaction->transaction = transaction_create_clone(trans);
		transaction_order(transaction->transaction, 0);
	} else {
		transaction->transaction = transaction_create(trans->pool);
	}

	return transaction;
}

void pakfire_transaction_free(PakfireTransaction transaction) {
	transaction_free(transaction->transaction);
	pakfire_free(transaction);
}

int pakfire_transaction_count(PakfireTransaction transaction) {
	return transaction->transaction->steps.count;
}

int pakfire_transaction_installsizechange(PakfireTransaction transaction) {
	int sizechange = transaction_calc_installsizechange(transaction->transaction);
	printf("SIZECHANGE %d\n", sizechange);

	// Convert from kbytes to bytes
	return sizechange * 1024;
}

PakfireStep pakfire_transaction_get_step(PakfireTransaction transaction, int index) {
	Transaction* trans = transaction->transaction;

	if (index >= trans->steps.count)
		return NULL;

	return pakfire_step_create(transaction, trans->steps.elements[index]);
}

PakfirePackageList pakfire_transaction_get_packages(PakfireTransaction transaction, int type) {
	PakfirePool pool = pakfire_transaction_pool(transaction);
	Transaction* trans = transaction->transaction;

	PakfirePackageList packagelist = pakfire_packagelist_create();

	for (int i = 0; i < trans->steps.count; i++) {
		Id p = trans->steps.elements[i];
		Id t = transaction_type(trans, p,
			SOLVER_TRANSACTION_SHOW_ACTIVE|SOLVER_TRANSACTION_CHANGE_IS_REINSTALL);

		if (t == type) {
			PakfirePackage package = pakfire_package_create(pool, p);
			pakfire_packagelist_push(packagelist, package);
		}
	}

	return packagelist;
}
