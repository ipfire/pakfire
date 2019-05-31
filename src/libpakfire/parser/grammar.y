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

%parse-param {PakfireParser parser}

// Generate verbose error messages
%error-verbose

%{
#include <stdio.h>

#include <pakfire/constants.h>
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
static void yyerror(PakfireParser parser, const char* s);

static void cleanup(void);
#define ABORT do { cleanup(); YYABORT; } while (0);

char* current_block = NULL;
static char* pakfire_parser_make_canonical_name(const char* name);

enum operator {
	OP_EQUALS = 0,
};

static PakfireParser new_parser(PakfireParser parent);
static PakfireParser make_if_stmt(PakfireParser parser, const enum operator op,
	const char* val1, const char* val2, PakfireParser block);

%}

%token							T_APPEND
%token							T_ASSIGN
%token <string>					T_DEFINE
%token <string>					T_END
%token <string>					T_EQUALS
%token <string>					T_IF
%token							T_EOL
%token <string>					T_WORD

%type <string>					define;
%type <string>					line;
%type <string>					text;
%type <string>					variable;
%type <string>					value;
%type <string>					word;
%type <string>					words;

%type <parser>					assignment;
%type <parser>					block_assignments;
%type <parser>					block_assignment;
%type <parser>					if_stmt;

%precedence T_WORD

%left T_APPEND
%left T_ASSIGN

%union {
	PakfireParser parser;
	char* string;
}

%%

top							: %empty
							| top assignment
							| top block
							| top empty
							;

empty						: T_EOL
							;

variable					: T_WORD;

value						: words
							| %empty
							{
								$$ = NULL;
							};

							// IF can show up in values and therefore this
							// hack is needed to parse those properly
word						: T_WORD;

words						: word
							| words word
							{
								int r = asprintf(&$$, "%s %s", $1, $2);
								if (r < 0) {
									Pakfire pakfire = pakfire_parser_get_pakfire(parser);
									ERROR(pakfire, "Could not allocate memory");
									pakfire_unref(pakfire);
									ABORT;
								}
							};

line						: words T_EOL
							{
								// Only forward words
								$$ = $1;
							}
							| T_EOL {
								$$ = "";
							};

text						: text line
							{
								int r = asprintf(&$$, "%s\n%s", $1, $2);
								if (r < 0) {
									Pakfire pakfire = pakfire_parser_get_pakfire(parser);
									ERROR(pakfire, "Could not allocate memory");
									pakfire_unref(pakfire);
									ABORT;
								}
							}
							| line
							;

end							: T_END T_EOL;

if_stmt						: T_IF T_WORD T_EQUALS T_WORD T_EOL block_assignments end
							{
								$$ = make_if_stmt(parser, OP_EQUALS, $2, $4, $6);
								pakfire_parser_unref($6);
							};

block_opening				: variable T_EOL
							{
								current_block = pakfire_strdup($1);
							};

block_closing				: end
							{
								pakfire_free(current_block);
								current_block = NULL;
							};

block						: block_opening block_assignments block_closing;

block_assignments			: block_assignments block_assignment
							{
								$$ = pakfire_parser_merge($1, $2);
								pakfire_parser_unref($2);
							}
							| block_assignment;

block_assignment			: assignment
							| if_stmt
							| empty
							{
								$$ = new_parser(parser);
							};

assignment					: variable T_ASSIGN value T_EOL
							{
								char* name = pakfire_parser_make_canonical_name($1);
								if (!name)
									ABORT;

								// Allocate a new parser
								// XXX should not inherit from parser
								$$ = new_parser(parser);

								int r = pakfire_parser_set_declaration($$, name, $3);
								pakfire_free(name);

								if (r < 0) {
									pakfire_parser_unref($$);
									ABORT;
								}
							}
							| variable T_APPEND value T_EOL
							{
								char* name = pakfire_parser_make_canonical_name($1);
								if (!name)
									ABORT;

								// Allocate a new parser
								// XXX should not inherit from parser
								$$ = new_parser(parser);

								int r = pakfire_parser_append_declaration($$, name, $3);
								pakfire_free(name);

								if (r < 0) {
									pakfire_parser_unref($$);
									ABORT;
								}
							}
							| define text end
							{
								char* name = pakfire_parser_make_canonical_name($1);
								if (!name)
									ABORT;

								// Allocate a new parser
								// XXX should not inherit from parser
								$$ = new_parser(parser);

								int r = pakfire_parser_set_declaration($$, name, $2);
								pakfire_free(name);

								if (r < 0) {
									pakfire_parser_unref($$);
									ABORT;
								}
							};

define						: T_DEFINE variable T_EOL
							{
								$$ = $2;
							};

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

int pakfire_parser_parse_data(PakfireParser parser, const char* data, size_t len) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parser);

	DEBUG(pakfire, "Parsing the following data:\n%s\n", data);

	num_lines = 1;

	YY_BUFFER_STATE buffer = yy_scan_bytes(data, len);
	int r = yyparse(parser);
	yy_delete_buffer(buffer);

	pakfire_unref(pakfire);

	return r;
}

void yyerror(PakfireParser parser, const char* s) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parser);

	ERROR(pakfire, "Error (line %d): %s\n", num_lines, s);

	pakfire_unref(pakfire);
}

static PakfireParser new_parser(PakfireParser parent) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parent);

	PakfireParser parser = pakfire_parser_create(pakfire, parent);
	pakfire_unref(pakfire);

	return parser;
}

static PakfireParser make_if_stmt(PakfireParser parser, const enum operator op,
		const char* val1, const char* val2, PakfireParser block) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parser);

	switch (op) {
		case OP_EQUALS:
			DEBUG(pakfire, "Evaluating if statement: %s == %s?\n", val1, val2);
			break;
	}

	const char* namespace = current_block;

	// Expand values
	char* v1 = pakfire_parser_expand(parser, namespace, val1);
	char* v2 = pakfire_parser_expand(parser, namespace, val2);

	PakfireParser result = NULL;

	switch (op) {
		case OP_EQUALS:
			DEBUG(pakfire, "  '%s' == '%s'?\n", v1, v2);

			if (strcmp(v1, v2) == 0)
				result = block;

			break;
	}

	pakfire_unref(pakfire);
	pakfire_free(v1);
	pakfire_free(v2);

	if (result)
		result = pakfire_parser_ref(result);

	return result;
}
