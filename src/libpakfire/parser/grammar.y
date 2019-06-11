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
#include <time.h>

#include <pakfire/constants.h>
#include <pakfire/logging.h>
#include <pakfire/parser.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define YYERROR_VERBOSE 1

#define YYDEBUG 0
#if ENABLE_DEBUG && YYDEBUG
	int yydebug = 1;
#endif

typedef struct yy_buffer_state* YY_BUFFER_STATE;
extern YY_BUFFER_STATE yy_scan_bytes(const char* buffer, size_t len);
extern void yy_delete_buffer(YY_BUFFER_STATE buffer);

extern int yylex();
extern int yyparse();

extern int num_lines;
static void yyerror(PakfireParser parser, const char* s);

#define ABORT do { YYABORT; } while (0);

enum operator {
	OP_EQUALS = 0,
};

static PakfireParser make_if_stmt(PakfireParser parser, const enum operator op,
	const char* val1, const char* val2, PakfireParser if_block, PakfireParser else_block);

static PakfireParser make_child(PakfireParser parent, const char* namespace);

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

%type <parser>					grammar;

%type <parser>					if_stmt;
%type <parser>					else_stmt;

%precedence T_WORD

%left T_APPEND
%left T_ASSIGN

%union {
	PakfireParser parser;
	char* string;
}

%%

grammar						: grammar statements
							| statements
							{
								$$ = parser;
							}
							;

statements					: statement
							| if_stmt
							| block
							| empty;

empty						: T_EOL
							;

variable					: T_WORD;

value						: words
							| %empty
							{
								$$ = NULL;
							};

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

if							: T_IF
							{
								// Open a new block
								parser = make_child(parser, NULL);
							};

else						: T_ELSE T_EOL
							{
								// Close the if block
								parser = pakfire_parser_get_parent(parser);

								// Open a new else block
								parser = make_child(parser, NULL);
							};

end							: T_END T_EOL;

if_stmt						: if variable T_EQUALS variable T_EOL grammar else_stmt end
							{
								PakfireParser result = make_if_stmt(parser, OP_EQUALS, $2, $4, $6, $7);

								// Close the whole if/else block
								parser = pakfire_parser_get_parent(parser);

								if (result)
									pakfire_parser_merge(parser, result);

								pakfire_parser_unref($6);
								pakfire_parser_unref($7);
							}
							;

else_stmt					: else grammar
							{
								$$ = $2;
							}
							| %empty
							{
								$$ = NULL;
							}
							;

block						: block_opening grammar end
							{
								// Move back to the parent parser
								parser = pakfire_parser_get_parent(parser);

								// Merge block into the parent parser
								pakfire_parser_merge(parser, $2);

								// Free block parser
								pakfire_parser_unref($2);
							};

block_opening				: variable T_EOL
							{
								// Create a new sub-parser which opens a new namespace
								parser = make_child(parser, $1);
							};

statement					: variable T_ASSIGN value T_EOL
							{
								int r = pakfire_parser_set(parser, $1, $3);
								if (r < 0)
									ABORT;
							}
							| variable T_APPEND value T_EOL
							{
								int r = pakfire_parser_append(parser, $1, $3);
								if (r < 0)
									ABORT;
							}
							| define text end
							{
								int r = pakfire_parser_set(parser, $1, $2);
								if (r < 0)
									ABORT;
							};

define						: T_DEFINE variable T_EOL
							{
								$$ = $2;
							};

%%

int pakfire_parser_parse_data(PakfireParser parent, const char* data, size_t len) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parent);

	DEBUG(pakfire, "Parsing the following data (%zu):\n%.*s\n",
		len, (int)len, data);

	// Save start time
	clock_t t_start = clock();

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

	// Save end time
	clock_t t_end = clock();

	// Destroy the parser
	pakfire_parser_unref(parser);

	// Log what we have in the parent parser now
	char* dump = pakfire_parser_dump(parent);

	DEBUG(pakfire, "Status of the parser %p:\n%s\n", parent, dump);
	pakfire_free(dump);

	// Log time we needed to parse data
	DEBUG(pakfire, "Parser finished in %.4fms\n",
		(double)(t_end - t_start) * 1000 / CLOCKS_PER_SEC);

	// Cleanup
	pakfire_unref(pakfire);

	return r;
}

void yyerror(PakfireParser parser, const char* s) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parser);

	ERROR(pakfire, "Error (line %d): %s\n", num_lines, s);

	pakfire_unref(pakfire);
}

static PakfireParser make_if_stmt(PakfireParser parser, const enum operator op,
		const char* val1, const char* val2, PakfireParser if_block, PakfireParser else_block) {
	Pakfire pakfire = pakfire_parser_get_pakfire(parser);

	switch (op) {
		case OP_EQUALS:
			DEBUG(pakfire, "Evaluating if statement: %s == %s?\n", val1, val2);
			break;
	}

	DEBUG(pakfire, "  parser = %p, if = %p, else = %p\n", parser, if_block, else_block);

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

	return result;
}

static PakfireParser make_child(PakfireParser parent, const char* namespace) {
	PakfireParser parser = pakfire_parser_create_child(parent, namespace);
	pakfire_parser_unref(parent);

	return parser;
}
