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

#include <pakfire/logging.h>
#include <pakfire/parser.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define YYERROR_VERBOSE 1

typedef struct yy_buffer_state* YY_BUFFER_STATE;
extern YY_BUFFER_STATE yy_scan_bytes(const char* buffer, size_t len);
extern void yy_delete_buffer(YY_BUFFER_STATE buffer);

extern int yylex();
extern int yyparse();

extern int num_lines;
static Pakfire pakfire;
static void yyerror(const char* s);

static void cleanup(void);
#define ABORT do { cleanup(); YYABORT; } while (0);

#define NUM_DECLARATIONS 128
static int pakfire_parser_add_declaration(const char* name, const char* value);
static struct pakfire_parser_declaration* declarations[NUM_DECLARATIONS];
%}

%token APPEND
%token ASSIGN
%token DEFINE
%token END
%token NEWLINE
%token TAB
%token WHITESPACE
%token <string>					WORD

%type <string>					line;
%type <string>					text;
%type <string>					variable;
%type <string>					value;
%type <string>					words;

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

variable					: WORD
							{
								$$ = $1;
							};

value						: words
							{
								$$ = $1;
							}
							| /* empty */
							{
								$$ = NULL;
							};

words						: WORD
							{
								$$ = $1;
							}
							| words WHITESPACE WORD
							{
								int r = asprintf(&$$, "%s %s", $1, $3);
								if (r < 0) {
									ERROR(pakfire, "Could not allocate memory");
									ABORT;
								}
							}
							| /* empty */
							{
								$$ = NULL;
							};

line						: whitespace words NEWLINE
							{
								// Only forward words
								$$ = $2;
							};

text						: text line
							{
								int r = asprintf(&$$, "%s\n%s", $1, $2);
								if (r < 0) {
									ERROR(pakfire, "Could not allocate memory");
									ABORT;
								}
							}
							| line
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
							| assignments block_assignment
							| /* empty */
							;

assignment					: whitespace variable whitespace ASSIGN whitespace value whitespace NEWLINE
							{
								int r = pakfire_parser_add_declaration($2, $6);
								if (r < 0)
									ABORT;
							};

block_assignment			: whitespace DEFINE WHITESPACE variable NEWLINE text whitespace END NEWLINE
							{
								int r = pakfire_parser_add_declaration($4, $6);
								if (r < 0)
									ABORT;
							}

%%

static void cleanup(void) {
	// Reset Pakfire pointer
	pakfire = NULL;

	// Free all declarations
	for (unsigned int i = 0; i < NUM_DECLARATIONS; i++) {
		pakfire_free(declarations[i]);
	}
}

static int pakfire_parser_add_declaration(const char* name, const char* value) {
	struct pakfire_parser_declaration* d;
	unsigned int i = 0;

	while (i++ < NUM_DECLARATIONS && declarations[i])
		i++;

	if (i == NUM_DECLARATIONS) {
		ERROR(pakfire, "No free declarations left\n");
		return -1;
	}

	// Allocate a new declaration
	declarations[i] = d = pakfire_calloc(1, sizeof(*d));
	if (!d)
		return -1;

	// Import name & value
	d->name  = pakfire_strdup(name);
	d->value = pakfire_strdup(value);

	DEBUG(pakfire, "New declaration: %s = %s\n", d->name, d->value);

	return 0;
}

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
