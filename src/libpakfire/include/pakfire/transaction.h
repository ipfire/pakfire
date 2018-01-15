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

PakfireTransaction pakfire_transaction_create(Pakfire pakfire, Transaction* trans);
PakfireTransaction pakfire_transaction_ref(PakfireTransaction transaction);
PakfireTransaction pakfire_transaction_unref(PakfireTransaction transaction);

PakfirePool pakfire_transaction_get_pool(PakfireTransaction transaction);
size_t pakfire_transaction_count(PakfireTransaction transaction);

ssize_t pakfire_transaction_installsizechange(PakfireTransaction transaction);

PakfireStep pakfire_transaction_get_step(PakfireTransaction transaction, unsigned int index);
PakfirePackageList pakfire_transaction_get_packages(PakfireTransaction transaction, pakfire_step_type_t type);

char* pakfire_transaction_dump(PakfireTransaction transaction, size_t width);

int pakfire_transaction_run(PakfireTransaction transaction);

#ifdef PAKFIRE_PRIVATE

Transaction* pakfire_transaction_get_transaction(PakfireTransaction transaction);

#endif

#endif /* PAKFIRE_TRANSACTION_H */
