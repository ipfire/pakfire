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

#ifndef PAKFIRE_SELECTOR_H
#define PAKFIRE_SELECTOR_H

#include <solv/pool.h>
#include <solv/queue.h>

#include <pakfire/filter.h>
#include <pakfire/packagelist.h>

PakfireSelector pakfire_selector_create(Pakfire pakfire);

PakfireSelector pakfire_selector_ref(PakfireSelector selector);
PakfireSelector pakfire_selector_unref(PakfireSelector selector);

int pakfire_selector_set(PakfireSelector selector, int keyname, int cmp_type, const char* match);

PakfirePackageList pakfire_selector_providers(PakfireSelector selector);

int pakfire_selector2queue(const PakfireSelector selector, Queue* queue, int solver_action);

#endif /* PAKFIRE_SELECTOR_H */
