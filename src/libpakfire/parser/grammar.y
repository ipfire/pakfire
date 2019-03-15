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

%glr-parser

%parse-param {Pakfire pakfire} {struct pakfire_parser_declaration** declarations}

// Generate verbose error messages
%error-verbose

%{
#include <stdio.h>

#include <pakfire/logging.h>
#include <pakfire/parser.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define YYERROR_VERBOSE 1

#define YYDEBUG 1
#if ENABLE_DEBUG
	int yydebug = 1;
#endif

typedef struct yy_buffer_state* YY_BUFFER_STATE;
extern YY_BUFFER_STATE yy_scan_bytes(const char* buffer, size_t len);
extern void yy_delete_buffer(YY_BUFFER_STATE buffer);

extern int yylex();
extern int yyparse();

extern int num_lines;
static void yyerror(Pakfire pakfire, struct pakfire_parser_declaration** declarations, const char* s);

static void cleanup(void);
#define ABORT do { cleanup(); YYABORT; } while (0);

#define NUM_DECLARATIONS 128
static int pakfire_parser_add_declaration(Pakfire pakfire,
 	struct pakfire_parser_declaration** delcarations, const char* name, const char* value);
static int pakfire_parser_append_declaration(Pakfire pakfire,
	struct pakfire_parser_declaration** declarations, const char* name, const char* value);

char* current_block = NULL;
%}

%token APPEND
%token ASSIGN
%token DEFINE
%token END
%token <string>					EQUALS
%token <string>					IF
%token NEWLINE
%token <string>					WORD

%type <string>					define;
%type <string>					line;
%type <string>					text;
%type <string>					variable;
%type <string>					value;
%type <string>					word;
%type <string>					words;

%precedence WORD

%left APPEND
%left ASSIGN

%union {
	char* string;
}

%%

top							: top thing
							| thing
							;

thing						: assignment
							| block
							| empty
							;

empty						: NEWLINE
							;

variable					: WORD;

value						: words
							| %empty
							{
								$$ = NULL;
							};

							// IF can show up in values and therefore this
							// hack is needed to parse those properly
word						: WORD | IF;

words						: word
							| words word
							{
								int r = asprintf(&$$, "%s %s", $1, $2);
								if (r < 0) {
									ERROR(pakfire, "Could not allocate memory");
									ABORT;
								}
							};

line						: words NEWLINE
							{
								// Only forward words
								$$ = $1;
							}
							| NEWLINE {
								$$ = NULL;
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
							;

if_stmt						: IF WORD EQUALS WORD NEWLINE block_assignments end
							{
								printf("IF STATEMENT NOT EVALUATED, YET: %s %s\n", $2, $4);
							};

block_opening				: variable NEWLINE
							{
								current_block = pakfire_strdup($1);
							};

block_closing				: END NEWLINE
							{
								pakfire_free(current_block);
								current_block = NULL;
							};

block						: block_opening block_assignments block_closing;

block_assignments			: block_assignments block_assignment
							| block_assignment;

block_assignment			: assignment
							| if_stmt
							| empty;

assignment					: variable ASSIGN value NEWLINE
							{
								int r = pakfire_parser_add_declaration(pakfire, declarations, $1, $3);
								if (r < 0)
									ABORT;
							}
							| variable APPEND value NEWLINE
							{
								int r = pakfire_parser_append_declaration(pakfire, declarations, $1, $3);
								if (r < 0)
									ABORT;
							}
							| define text end
							{
								int r = pakfire_parser_add_declaration(pakfire, declarations, $1, $2);
								if (r < 0)
									ABORT;
							};

define						: DEFINE variable NEWLINE
							{
								$$ = $2;
							}
							| variable NEWLINE
							{
								$$ = $1;
							};

end							: END NEWLINE;

%%

static void cleanup(void) {
	// Reset current_block
	if (current_block) {
		pakfire_free(current_block);
		current_block = NULL;
	}
}

static char* pakfire_parser_make_canonical_name(const char* name) {
	char* buffer = NULL;

	if (current_block) {
		int r = asprintf(&buffer, "%s.%s", current_block, name);
		if (r < 0)
			return NULL;
	} else {
		buffer = pakfire_strdup(name);
	}

	return buffer;
}

static struct pakfire_parser_declaration* pakfire_parser_get_declaration(Pakfire pakfire,
		struct pakfire_parser_declaration** declarations, const char* name) {
	if (!declarations)
		return NULL;

	char* canonical_name = pakfire_parser_make_canonical_name(name);

	struct pakfire_parser_declaration* d = *declarations;
	while (d) {
		if (strcmp(d->name, canonical_name) == 0) {
			goto END;
		}

		d++;
	}

END:
	pakfire_free(canonical_name);

	return d;
}

static int pakfire_parser_add_declaration(Pakfire pakfire,
		struct pakfire_parser_declaration** declarations, const char* name, const char* value) {
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
	d->name = pakfire_parser_make_canonical_name(name);
	d->value = pakfire_strdup(value);

	DEBUG(pakfire, "New declaration: %s = %s\n", d->name, d->value);

	return 0;
}

static int pakfire_parser_append_declaration(Pakfire pakfire,
		struct pakfire_parser_declaration** declarations, const char* name, const char* value) {
	struct pakfire_parser_declaration* d = pakfire_parser_get_declaration(pakfire, declarations, name);

	// Add the declaration if we could not find it
	if (!d)
		return pakfire_parser_add_declaration(pakfire, declarations, name, value);

	char* buffer = NULL;

	// Concat value
	int r = asprintf(&buffer, "%s %s", d->value, value);
	if (r < 0)
		return r;

	DEBUG(pakfire, "Appended declaration: %s = %s (was: %s)\n", d->name, buffer, d->value);

	// Replace value in declaration
	if (d->value)
		pakfire_free(d->value);

	d->value = buffer;

	return 0;
}

struct pakfire_parser_declaration** pakfire_parser_parse_metadata(Pakfire pakfire, const char* data, size_t len) {
	DEBUG(pakfire, "Parsing the following data:\n%s\n", data);

	num_lines = 1;

	// Reserve some space for parsed declarations
	struct pakfire_parser_declaration** declarations = \
		pakfire_calloc(NUM_DECLARATIONS, sizeof(*declarations));

	YY_BUFFER_STATE buffer = yy_scan_bytes(data, len);
	int r = yyparse(pakfire, declarations);
	yy_delete_buffer(buffer);

	// Cleanup declarations in case of an error
	if (r) {
		for (unsigned int i = 0; i < NUM_DECLARATIONS; i++) {
			if (declarations[i])
				pakfire_free(declarations[i]);
		}

		pakfire_free(declarations);

		// Return nothing
		return NULL;
	}

	return declarations;
}

void yyerror(Pakfire pakfire, struct pakfire_parser_declaration** declarations, const char* s) {
	ERROR(pakfire, "Error (line %d): %s\n", num_lines, s);
}
