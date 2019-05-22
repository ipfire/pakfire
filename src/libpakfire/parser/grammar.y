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
#include <regex.h>
#include <stdio.h>

#include <pakfire/constants.h>
#include <pakfire/logging.h>
#include <pakfire/parser.h>
#include <pakfire/types.h>
#include <pakfire/util.h>

#define VARIABLE_PATTERN "%\\{([A-Za-z0-9_\\-]+)\\}"

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

%precedence T_WORD

%left T_APPEND
%left T_ASSIGN

%union {
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
									ERROR(pakfire, "Could not allocate memory");
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
									ERROR(pakfire, "Could not allocate memory");
									ABORT;
								}
							}
							| line
							;

end							: T_END T_EOL;

if_stmt						: T_IF T_WORD T_EQUALS T_WORD T_EOL block_assignments end
							{
								printf("IF STATEMENT NOT EVALUATED, YET: %s %s\n", $2, $4);
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
							| block_assignment;

block_assignment			: assignment
							| if_stmt
							| empty;

assignment					: variable T_ASSIGN value T_EOL
							{
								int r = pakfire_parser_add_declaration(pakfire, declarations, $1, $3);
								if (r < 0)
									ABORT;
							}
							| variable T_APPEND value T_EOL
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

static char* pakfire_parser_split_namespace(char* s) {
	char* pos = strrpos(s, '.');

	if (pos) {
		s[s - pos] = '\0';
	}

	return s;
}

static struct pakfire_parser_declaration* pakfire_parser_get_declaration(Pakfire pakfire,
		struct pakfire_parser_declaration** declarations, const char* name) {
	if (!declarations)
		return NULL;

	struct pakfire_parser_declaration* d = *declarations;
	while (d) {
		if (strcmp(d->name, name) == 0)
			return d;

		d++;
	}

	return NULL;
}

static struct pakfire_parser_declaration* pakfire_parser_get_declaration_in_namespace(
		Pakfire pakfire, struct pakfire_parser_declaration** declarations,
		const char* namespace, const char* name) {
	if (!namespace || !*namespace)
		return pakfire_parser_get_declaration(pakfire, declarations, name);

	char* n = pakfire_strdup(namespace);

	size_t length = strlen(n) + strlen(name) + 1;
	char* buffer = pakfire_malloc(length + 1);

	struct pakfire_parser_declaration* d = NULL;

	while (1) {
		if (n)
			snprintf(buffer, length + 1, "%s.%s", n, name);
		else
			snprintf(buffer, length + 1, "%s", name);

		DEBUG(pakfire, "Looking up %s\n", buffer);

		// Lookup declaration
		d = pakfire_parser_get_declaration(pakfire, declarations, buffer);

		// End if we have found a match
		if (d)
			break;

		// End if we have hit the root namespace
		if (!n)
			break;

		/*
			If we did not find a match, we will remove one level of the
			namespace and try again...
		*/
		char* p = strrchr(n, '.');
		if (p) {
			n[p - n] = '\0';
		} else {
			pakfire_free(n);
			n = NULL;
		}
	}

	if (n)
		pakfire_free(n);
	pakfire_free(buffer);

	return d;
}

static char* pakfire_parser_expand_declaration(Pakfire pakfire,
		struct pakfire_parser_declaration** declarations,
		const struct pakfire_parser_declaration* declaration) {
	// Return NULL when the value of the declaration is NULL
	if (!declaration || !declaration->value)
		return NULL;

	// Compile the regular expression
	regex_t preg;
	int r = regcomp(&preg, VARIABLE_PATTERN, REG_EXTENDED);
	if (r) {
		char error[1024];
		regerror(r, &preg, error, sizeof(error));

		ERROR(pakfire, "Could not compile regular expression (%s): %s",
			VARIABLE_PATTERN, error);

		return NULL;
	}

	char* namespace = pakfire_strdup(declaration->name);
	char* p = strrchr(namespace, '.');
	if (p)
		namespace[p - namespace] = '\0';
	else
		namespace[0] = '\0';

	// Create a working copy of the string we are expanding
	char* buffer = pakfire_strdup(declaration->value);

	const size_t max_groups = 2;
	regmatch_t groups[max_groups];

	// Search for any variables
	while (1) {
		// Perform matching
		r = regexec(&preg, buffer, max_groups, groups, 0);

		// End loop when we have expanded all variables
		if (r == REG_NOMATCH) {
			DEBUG(pakfire, "No (more) matches found in: %s\n", buffer);
			break;
		}

		// Set offsets to the matched variable name
		off_t start = groups[1].rm_so, end = groups[1].rm_eo;

		// Get the name of the variable
		char* variable = pakfire_malloc(end - start + 1);
		snprintf(variable, end - start + 1, "%s", buffer + start);

		DEBUG(pakfire, "Expanding variable: %s\n", variable);

		// Search for a declaration of this variable
		struct pakfire_parser_declaration* v =
			pakfire_parser_get_declaration_in_namespace(pakfire, declarations, namespace, variable);

		DEBUG(pakfire, "v = %p\n", v);

		const char* value = NULL;
		if (v && v->value) {
			DEBUG(pakfire, "Replacing %%{%s} with %s = '%s'\n",
				variable, v->name, value);
			value = v->value;
		} else {
			DEBUG(pakfire, "Replacing %%{%s} with an empty string\n", variable);
		}

		// Reset offsets to the whole matched string
		start = groups[0].rm_so; end = groups[0].rm_eo;

		// Length of the new buffer
		size_t length = strlen(buffer) - (end - start) + ((value) ? strlen(value) : 0);

		char* b = pakfire_malloc(length + 1);

		// Copy buffer up to the beginning of the match
		snprintf(b, start + 1, "%s", buffer);

		// Append the new value (if any)
		if (value)
			strcat(b, value);

		// Append the rest of the buffer
		if (buffer + end)
			strcat(b, buffer + end);

		DEBUG(pakfire, "New buffer: %s\n", b);

		// Drop old buffer
		pakfire_free(buffer);
		buffer = b;
	}

	regfree(&preg);

	return buffer;
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

char* pakfire_parser_get(Pakfire pakfire,
		struct pakfire_parser_declaration** declarations, const char* name) {
	struct pakfire_parser_declaration* declaration = pakfire_parser_get_declaration(pakfire, declarations, name);

	// Return NULL when nothing was found
	if (!declaration)
		return NULL;

	// Otherwise return the expanded value
	return pakfire_parser_expand_declaration(pakfire, declarations, declaration);
}
