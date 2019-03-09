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
#include <pakfire/logging.h>
#include <pakfire/types.h>

#define YYERROR_VERBOSE 1

typedef struct yy_buffer_state* YY_BUFFER_STATE;
extern YY_BUFFER_STATE yy_scan_bytes(const char* buffer, size_t len);
extern void yy_delete_buffer(YY_BUFFER_STATE buffer);

extern int yylex();
extern int yyparse();

extern int num_lines;
static Pakfire pakfire;
static void yyerror(const char* s);
%}

%token APPEND
%token ASSIGN
%token DEFINE
%token END
%token NEWLINE
%token TAB
%token <string>					VARIABLE
%token <string>					VALUE
%token WHITESPACE

%type <string>					variable;
%type <string>					value;

%union {
	char* string;
}

%%

top							: top empty
							| top block
							| empty
							| block
							;

empty						: WHITESPACE NEWLINE
							| NEWLINE
							;

// Optional whitespace
whitespace					: WHITESPACE
							| /* empty */
							;

variable					: VARIABLE
							{
								$$ = $1;
							};

value						: VALUE
							| variable
							{
								$$ = $1;
							}
							| /* empty */
							{
								$$ = NULL;
							};

block_opening				: variable NEWLINE
							{
								printf("BLOCK OPEN: %s\n", $1);
							};

block_closing				: END NEWLINE
							{
								printf("BLOCK CLOSED\n");
							}

block						: block_opening assignments block_closing
							{
								printf("BLOCK FOUND\n");
							};

assignments					: assignments assignment
							| assignments empty
							| /* empty */
							;

assignment					: whitespace variable whitespace ASSIGN whitespace value whitespace NEWLINE
							{
								printf("ASSIGNMENT FOUND: %s = %s\n", $2, $6);
							};

%%

int pakfire_parser_parse_metadata(Pakfire _pakfire, const char* data, size_t len) {
	pakfire = _pakfire;

	DEBUG(pakfire, "Parsing the following data:\n%s\n", data);

	num_lines = 1;

	YY_BUFFER_STATE buffer = yy_scan_bytes(data, len);
	int r = yyparse();
	yy_delete_buffer(buffer);

	return r;
}

void yyerror(const char* s) {
	ERROR(pakfire, "Error (line %d): %s\n", num_lines, s);
}
