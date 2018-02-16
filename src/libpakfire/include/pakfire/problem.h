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

#ifndef PAKFIRE_PROBLEM_H
#define PAKFIRE_PROBLEM_H

#include <pakfire/request.h>

PakfireProblem pakfire_problem_create(PakfireRequest request, Id id);
PakfireProblem pakfire_problem_ref(PakfireProblem problem);
PakfireProblem pakfire_problem_unref(PakfireProblem problem);

PakfireProblem pakfire_problem_next(PakfireProblem problem);
void pakfire_problem_append(PakfireProblem problem, PakfireProblem new_problem);

const char* pakfire_problem_to_string(PakfireProblem problem);

PakfireRequest pakfire_problem_get_request(PakfireProblem problem);
PakfireSolution pakfire_problem_get_solutions(PakfireProblem problem);

#ifdef PAKFIRE_PRIVATE

#include <solv/pooltypes.h>

Pakfire pakfire_problem_get_pakfire(PakfireProblem problem);
Id pakfire_problem_get_id(PakfireProblem problem);

#endif

#endif /* PAKFIRE_PROBLEM_H */
