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

#ifndef PAKFIRE_TRANSACTION_H
#define PAKFIRE_TRANSACTION_H

#include <solv/transaction.h>

#include <pakfire/types.h>

PakfireTransaction pakfire_transaction_create(PakfirePool pool, Transaction* trans);
void pakfire_transaction_free(PakfireTransaction transaction);

int pakfire_transaction_count(PakfireTransaction transaction);

int pakfire_transaction_installsizechange(PakfireTransaction transaction);

PakfireStep pakfire_transaction_get_step(PakfireTransaction transaction, int index);
PakfirePackageList pakfire_transaction_get_packages(PakfireTransaction transaction, int type);

#ifdef PAKFIRE_PRIVATE

struct _PakfireTransaction {
	PakfirePool pool;
	Transaction* transaction;
};

static inline PakfirePool pakfire_transaction_pool(PakfireTransaction transaction) {
	return transaction->pool;
}

#endif

#endif /* PAKFIRE_TRANSACTION_H */
