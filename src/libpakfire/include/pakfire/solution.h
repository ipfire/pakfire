/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2017 Pakfire development team                                 #
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

#ifndef PAKFIRE_SOLUTION_H
#define PAKFIRE_SOLUTION_H

#include <pakfire/problem.h>

PakfireSolution pakfire_solution_create(PakfireProblem problem, Id id);
PakfireSolution pakfire_solution_ref(PakfireSolution solution);
void pakfire_solution_free(PakfireSolution solution);

PakfireSolution pakfire_solution_next(PakfireSolution solution);
void pakfire_solution_append(PakfireSolution solution, PakfireSolution new_solution);

char* pakfire_solution_to_string(PakfireSolution solution);

#endif /* PAKFIRE_SOLUTION_H */
