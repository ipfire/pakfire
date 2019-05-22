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

#include <regex.h>
#include <string.h>

#include <pakfire/errno.h>
#include <pakfire/logging.h>
#include <pakfire/parser.h>
#include <pakfire/pakfire.h>
#include <pakfire/private.h>
#include <pakfire/util.h>

#define NUM_DECLARATIONS 1024
#define VARIABLE_PATTERN "%\\{([A-Za-z0-9_\\-]+)\\}"

struct _PakfireParser {
	Pakfire pakfire;
	int nrefs;

	struct pakfire_parser_declaration** declarations;
	unsigned int next_declaration;
	unsigned int num_declarations;
};

PAKFIRE_EXPORT PakfireParser pakfire_parser_create(Pakfire pakfire) {
	PakfireParser parser = pakfire_calloc(1, sizeof(*parser));
	if (parser) {
		parser->pakfire = pakfire_ref(pakfire);

		parser->num_declarations = NUM_DECLARATIONS;

		// Allocate a decent number of declarations
		parser->declarations = pakfire_calloc(
			parser->num_declarations, sizeof(*parser->declarations));

		parser->next_declaration = 0;
	}

	return parser;
}

Pakfire pakfire_parser_get_pakfire(PakfireParser parser) {
	return pakfire_ref(parser->pakfire);
}

static void pakfire_parser_free_declarations(
		struct pakfire_parser_declaration** declarations, unsigned int num) {
	for (unsigned int i = 0; i < num; i++) {
		if (declarations[i])
			pakfire_free(declarations[i]);
	}

	pakfire_free(declarations);
}

static void pakfire_parser_free(PakfireParser parser) {
	DEBUG(parser->pakfire, "Releasing parser at %p\n", parser);

	pakfire_parser_free_declarations(parser->declarations, parser->num_declarations);

	pakfire_unref(parser->pakfire);
	pakfire_free(parser);
}

PAKFIRE_EXPORT PakfireParser pakfire_parser_unref(PakfireParser parser) {
	if (!parser)
		return NULL;

	if (--parser->nrefs > 0)
		return parser;

	pakfire_parser_free(parser);
	return NULL;
}

static struct pakfire_parser_declaration* pakfire_parser_get_declaration(
		PakfireParser parser, const char* name) {
	struct pakfire_parser_declaration* d;

	for (unsigned i = 0; i < parser->num_declarations; i++) {
		d = parser->declarations[i];
		if (!d)
			break;

		// Compare the name
		if (strcmp(d->name, name) == 0)
			return d;
	}

	return NULL;
}

PAKFIRE_EXPORT int pakfire_parser_add_declaration(PakfireParser parser,
		const char* name, const char* value) {
	// Check if we have any space left
	if (parser->next_declaration >= parser->num_declarations) {
		ERROR(parser->pakfire, "No free declarations left\n");
		return -1;
	}

	// XXX handle when name already exists

	// Allocate a new declaration
	struct pakfire_parser_declaration* d = pakfire_calloc(1, sizeof(*d));
	if (!d)
		return -1;

	// Import name & value
	d->name = pakfire_strdup(name);
	d->value = pakfire_strdup(value);

	DEBUG(parser->pakfire, "New declaration: %s = %s\n", d->name, d->value);

	// Assign new declaration to array
	parser->declarations[parser->next_declaration++] = d;

	return 0;
}

PAKFIRE_EXPORT int pakfire_parser_append_declaration(PakfireParser parser,
		const char* name, const char* value) {
	struct pakfire_parser_declaration* d = pakfire_parser_get_declaration(parser, name);

	// Add the declaration if we could not find it
	if (!d)
		return pakfire_parser_add_declaration(parser, name, value);

	char* buffer = NULL;

	// Concat value
	int r = asprintf(&buffer, "%s %s", d->value, value);
	if (r < 0)
		return r;

	DEBUG(parser->pakfire, "Appended declaration: %s = %s (was: %s)\n",
		d->name, buffer, d->value);

	// Replace value in declaration
	if (d->value)
		pakfire_free(d->value);

	d->value = buffer;

	return 0;
}

static struct pakfire_parser_declaration* pakfire_parser_get_declaration_in_namespace(
		PakfireParser parser, const char* namespace, const char* name) {
	if (!namespace || !*namespace)
		return pakfire_parser_get_declaration(parser, name);

	char* n = pakfire_strdup(namespace);

	size_t length = strlen(n) + strlen(name) + 1;
	char* buffer = pakfire_malloc(length + 1);

	struct pakfire_parser_declaration* d = NULL;

	while (1) {
		if (n)
			snprintf(buffer, length + 1, "%s.%s", n, name);
		else
			snprintf(buffer, length + 1, "%s", name);

		DEBUG(parser->pakfire, "Looking up %s\n", buffer);

		// Lookup declaration
		d = pakfire_parser_get_declaration(parser, buffer);

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

static char* pakfire_parser_expand_declaration(PakfireParser parser,
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

		ERROR(parser->pakfire, "Could not compile regular expression (%s): %s",
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
			DEBUG(parser->pakfire, "No (more) matches found in: %s\n", buffer);
			break;
		}

		// Set offsets to the matched variable name
		off_t start = groups[1].rm_so, end = groups[1].rm_eo;

		// Get the name of the variable
		char* variable = pakfire_malloc(end - start + 1);
		snprintf(variable, end - start + 1, "%s", buffer + start);

		DEBUG(parser->pakfire, "Expanding variable: %s\n", variable);

		// Search for a declaration of this variable
		struct pakfire_parser_declaration* v =
			pakfire_parser_get_declaration_in_namespace(parser, namespace, variable);

		DEBUG(parser->pakfire, "v = %p\n", v);

		const char* value = NULL;
		if (v && v->value) {
			DEBUG(parser->pakfire, "Replacing %%{%s} with %s = '%s'\n",
				variable, v->name, value);
			value = v->value;
		} else {
			DEBUG(parser->pakfire, "Replacing %%{%s} with an empty string\n", variable);
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

		DEBUG(parser->pakfire, "New buffer: %s\n", b);

		// Drop old buffer
		pakfire_free(buffer);
		buffer = b;
	}

	regfree(&preg);

	return buffer;
}

PAKFIRE_EXPORT char* pakfire_parser_get(PakfireParser parser, const char* name) {
	struct pakfire_parser_declaration* d = pakfire_parser_get_declaration(parser, name);

	// Return NULL when nothing was found
	if (!d)
		return NULL;

	// Otherwise return the expanded value
	return pakfire_parser_expand_declaration(parser, d);
}

PAKFIRE_EXPORT int pakfire_parser_read(PakfireParser parser, FILE* f) {
	char* data;
	size_t len;

	int r = pakfire_read_file_into_buffer(f, &data, &len);
	if (r)
		return r;

	r = pakfire_parser_parse_data(parser, data, len);

	if (data)
		pakfire_free(data);

	return r;
}
