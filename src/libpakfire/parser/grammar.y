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

enum operator {
	OP_EQUALS = 0,
};

static PakfireParser new_parser(PakfireParser parent, const char* namespace);
static PakfireParser merge_parsers(PakfireParser p1, PakfireParser p2);

static PakfireParser make_if_stmt(PakfireParser parser, const enum operator op,
	const char* val1, const char* val2, PakfireParser if_block, PakfireParser else_block);

%}

%token							T_APPEND
%token							T_ASSIGN
%token							T_DEFINE
%token							T_END
%token 							T_EQUALS
%token							T_IF
%token							T_ELSE
%token							T_EOL
%token <string>					T_WORD

%type <string>					define;
%type <string>					line;
%type <string>					text;
%type <string>					variable;
%type <string>					value;
%type <string>					word;
%type <string>					words;

%type <parser>					top;
%type <parser>					item;
%type <parser>					assignment;
%type <parser>					block;
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

top							: top item
							{
								$$ = merge_parsers($1, $2);
							}
							| item
							{
								$$ = merge_parsers(parser, $1);
							}
							;

item						: assignment
							| block
							| empty {
								$$ = NULL;
							};

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

else						: T_ELSE T_EOL;

if_stmt						: T_IF T_WORD T_EQUALS T_WORD T_EOL block_assignments else block_assignments end
							{
								$$ = make_if_stmt(parser, OP_EQUALS, $2, $4, $6, $8);
								//pakfire_parser_unref($6);
								//pakfire_parser_unref($8);
							}
							| T_IF T_WORD T_EQUALS T_WORD T_EOL block_assignments end
							{
								$$ = make_if_stmt(parser, OP_EQUALS, $2, $4, $6, NULL);
								//pakfire_parser_unref($6);
							};

block_opening				: variable T_EOL
							{
								// Create a new sub-parser which opens a new namespace
								parser = new_parser(parser, $1);
							};

block_closing				: end
							{
								// Move back to the parent parser
								parser = pakfire_parser_get_parent(parser);
							};

block						: block_opening block_assignments block_closing
							{
								$$ = $2;
							};

block_assignments			: block_assignments block_assignment
							{
								$$ = merge_parsers($1, $2);
							}
							| block_assignment {
								if ($1)
									$$ = $1;
								else
									$$ = new_parser(parser, NULL);
							};

block_assignment			: assignment
							| block
							| if_stmt
							| empty
							{
								$$ = NULL;
							};

assignment					: variable T_ASSIGN value T_EOL
							{
								// Allocate a new parser
								$$ = new_parser(parser, NULL);

								int r = pakfire_parser_set($$, $1, $3);
								if (r < 0) {
									pakfire_parser_unref($$);
									ABORT;
								}
							}
							| variable T_APPEND value T_EOL
							{
								// Allocate a new parser
								$$ = new_parser(parser, NULL);

								int r = pakfire_parser_append($$, $1, $3);
								if (r < 0) {
									pakfire_parser_unref($$);
									ABORT;
								}
							}
							| define text end
							{
								// Allocate a new parser
								$$ = new_parser(parser, NULL);

								int r = pakfire_parser_set($$, $1, $2);
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
}

int pakfire_parser_parse_data(PakfireParser parent, const char* data, size_t len) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parent);

	DEBUG(pakfire, "Parsing the following data:\n%s\n", data);

	// Create a new sub-parser
	PakfireParser parser = pakfire_parser_create(pakfire, parent, NULL);

	num_lines = 1;

	YY_BUFFER_STATE buffer = yy_scan_bytes(data, len);
	int r = yyparse(parser);
	yy_delete_buffer(buffer);

	// If everything was parsed successfully, we merge the sub-parser into
	// the parent parser. That way, it will be untouched if something could
	// not be successfully parsed.
	if (r == 0) {
		parent = pakfire_parser_merge(parent, parser);
	}

	// Destroy the parser
	pakfire_parser_unref(parser);

	// Log what we have in the parent parser now
	char* dump = pakfire_parser_dump(parent);

	DEBUG(pakfire, "Status of the parser %p:\n%s\n", parent, dump);
	pakfire_free(dump);

	// Cleanup
	pakfire_unref(pakfire);

	return r;
}

void yyerror(PakfireParser parser, const char* s) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parser);

	ERROR(pakfire, "Error (line %d): %s\n", num_lines, s);

	pakfire_unref(pakfire);
}

static PakfireParser new_parser(PakfireParser parent, const char* namespace) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parent);

	PakfireParser parser = pakfire_parser_create(pakfire, parent, namespace);
	pakfire_unref(pakfire);

	return parser;
}

static PakfireParser merge_parsers(PakfireParser p1, PakfireParser p2) {
	PakfireParser p = NULL;

	if (p1 && p2)
		p = pakfire_parser_merge(p1, p2);
	else if (p1)
		p = p1;
	else if (p2)
		p = p2;

	return p;
}

static PakfireParser make_if_stmt(PakfireParser parser, const enum operator op,
		const char* val1, const char* val2, PakfireParser if_block, PakfireParser else_block) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parser);

	switch (op) {
		case OP_EQUALS:
			DEBUG(pakfire, "Evaluating if statement: %s == %s?\n", val1, val2);
			break;
	}

	// Expand values
	char* v1 = pakfire_parser_expand(parser, val1);
	char* v2 = pakfire_parser_expand(parser, val2);

	PakfireParser result = NULL;

	switch (op) {
		case OP_EQUALS:
			DEBUG(pakfire, "  '%s' == '%s'?\n", v1, v2);

			if (strcmp(v1, v2) == 0)
				result = if_block;
			else
				result = else_block;

			break;
	}

	pakfire_unref(pakfire);
	pakfire_free(v1);
	pakfire_free(v2);

	if (result)
		result = pakfire_parser_ref(result);

	return result;
}
