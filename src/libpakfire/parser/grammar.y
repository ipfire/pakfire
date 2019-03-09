/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2019 Pakfire development team                                 #
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

%{
#include <stdio.h>
#include <stdlib.h>

#include <pakfire/types.h>

#define YYERROR_VERBOSE 1

typedef struct yy_buffer_state* YY_BUFFER_STATE;
extern YY_BUFFER_STATE yy_scan_bytes(const char* buffer, size_t len);
extern void yy_delete_buffer(YY_BUFFER_STATE buffer);

extern int yylex();
extern int yyparse();
void yyerror(const char* s);
%}

%token APPEND
%token ASSIGN
%token DEFINE
%token END
%token NEWLINE
%token TAB
%token VARIABLE
%token VALUE
%token WHITESPACE

%%

top: NEWLINE

%%

int pakfire_parser_parse_metadata(Pakfire pakfire, const char* data, size_t len) {
	YY_BUFFER_STATE buffer = yy_scan_bytes(data, len);
	int r = yyparse();
	yy_delete_buffer(buffer);

	return r;
}

void yyerror(const char* s) {
	fprintf(stderr, "Parse error: %s\n", s);
	abort();
}
