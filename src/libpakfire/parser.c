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
	struct _PakfireParser* parent;
	int nrefs;

	char* namespace;

	struct pakfire_parser_declaration* declarations[NUM_DECLARATIONS];
	size_t next_declaration;
	size_t num_declarations;
};

static char* pakfire_parser_make_namespace(PakfireParser parent, const char* namespace) {
	char* buffer = NULL;

	if (parent && parent->namespace) {
		if (namespace)
			asprintf(&buffer, "%s.%s", parent->namespace, namespace);
		else
			buffer = pakfire_strdup(parent->namespace);
	} else {
		if (namespace)
			buffer = pakfire_strdup(namespace);
	}

	return buffer;
}

static char* pakfire_parser_make_canonical_name(PakfireParser parser, const char* name) {
	char* buffer = NULL;

	if (parser->namespace) {
		int r = asprintf(&buffer, "%s.%s", parser->namespace, name);
		if (r < 0)
			return NULL;
	} else {
		buffer = pakfire_strdup(name);
	}

	return buffer;
}

PAKFIRE_EXPORT PakfireParser pakfire_parser_create(Pakfire pakfire, PakfireParser parent, const char* namespace) {
	PakfireParser parser = pakfire_calloc(1, sizeof(*parser));
	if (parser) {
		parser->pakfire = pakfire_ref(pakfire);
		parser->nrefs = 1;

		// Store a reference to the parent parser if we have one
		if (parent)
			parser->parent = pakfire_parser_ref(parent);

		// Make namespace
		parser->namespace = pakfire_parser_make_namespace(parent, namespace);

		parser->num_declarations =
			sizeof(parser->declarations) / sizeof(*parser->declarations);
		parser->next_declaration = 0;

		DEBUG(pakfire, "Allocated new parser at %p (%s, %p)\n",
			parser, parser->namespace, parser->parent);
	}

	return parser;
}

PAKFIRE_EXPORT PakfireParser pakfire_parser_ref(PakfireParser parser) {
	++parser->nrefs;

	return parser;
}

Pakfire pakfire_parser_get_pakfire(PakfireParser parser) {
	return pakfire_ref(parser->pakfire);
}

static void pakfire_parser_free_declarations(PakfireParser parser) {
	for (unsigned int i = 0; i < parser->num_declarations; i++) {
		struct pakfire_parser_declaration* d = parser->declarations[i];

		// If we hit NULL, this is the end
		if (!d)
			break;

		// Free everything
		if (d->name)
			pakfire_free(d->name);
		if (d->value)
			pakfire_free(d->value);
		pakfire_free(d);
	}
}

static void pakfire_parser_free(PakfireParser parser) {
	DEBUG(parser->pakfire, "Releasing parser at %p\n", parser);

	pakfire_parser_free_declarations(parser);
	if (parser->namespace)
		pakfire_free(parser->namespace);

	pakfire_parser_unref(parser->parent);
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

PAKFIRE_EXPORT PakfireParser pakfire_parser_get_parent(PakfireParser parser) {
	if (parser->parent)
		return pakfire_parser_ref(parser->parent);

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

static int pakfire_parser_set_declaration(PakfireParser parser,
		const char* name, const char* value) {
	// Handle when name already exists
	struct pakfire_parser_declaration* d = pakfire_parser_get_declaration(parser, name);
	if (d) {
		// Replace value
		if (d->value)
			pakfire_free(d->value);
		d->value = pakfire_strdup(value);

		DEBUG(parser->pakfire, "Updated declaration: %s = %s\n",
			d->name, d->value);

		// All done
		return 0;
	}

	// Check if we have any space left
	if (parser->next_declaration >= parser->num_declarations) {
		ERROR(parser->pakfire, "No free declarations left\n");
		return -1;
	}

	// Allocate a new declaration
	d = pakfire_calloc(1, sizeof(*d));
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

PAKFIRE_EXPORT int pakfire_parser_set(PakfireParser parser, const char* name, const char* value) {
	char* canonical_name = pakfire_parser_make_canonical_name(parser, name);

	int r = pakfire_parser_set_declaration(parser, canonical_name, value);
	pakfire_free(canonical_name);

	return r;
}

PAKFIRE_EXPORT int pakfire_parser_append(PakfireParser parser,
		const char* name, const char* value) {
	struct pakfire_parser_declaration* d = pakfire_parser_get_declaration(parser, name);

	// Add the declaration if we could not find it
	if (!d)
		return pakfire_parser_set_declaration(parser, name, value);

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

static void pakfire_parser_strip_namespace(char* s) {
	char* pos = strrchr(s, '.');

	if (pos)
		s[pos - s] = '\0';
	else
		s[0] = '\0';
}

static struct pakfire_parser_declaration* pakfire_parser_find_declaration(
		PakfireParser parser, const char* name) {
	// Create a working copy of the namespace
	char* n = pakfire_strdup(parser->namespace);

	size_t length = ((n) ? strlen(n) : 0) + strlen(name) + 1;
	char* buffer = pakfire_malloc(length + 1);

	struct pakfire_parser_declaration* d = NULL;

	while (1) {
		if (n && *n)
			snprintf(buffer, length + 1, "%s.%s", n, name);
		else
			snprintf(buffer, length + 1, "%s", name);

		DEBUG(parser->pakfire, "Looking up %s\n", buffer);

		// Lookup declaration
		d = pakfire_parser_get_declaration(parser, buffer);

		// End if we have found a match
		if (d)
			break;

		// End if namespace is empty
		if (!n || !*n)
			break;

		/*
			If we did not find a match, we will remove one level of the
			namespace and try again...
		*/
		pakfire_parser_strip_namespace(n);
	}

	pakfire_free(buffer);

	if (n)
		pakfire_free(n);

	if (!d && parser->parent)
		d = pakfire_parser_find_declaration(parser->parent, name);

	return d;
}

PAKFIRE_EXPORT char* pakfire_parser_expand(PakfireParser parser, const char* value) {
	// Return NULL when the value is NULL
	if (!value)
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

	// Create a working copy of the string we are expanding
	char* buffer = pakfire_strdup(value);

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
			pakfire_parser_find_declaration(parser, variable);

		const char* value = NULL;
		if (v && v->value) {
			DEBUG(parser->pakfire, "Replacing %%{%s} with %s = '%s'\n",
				variable, v->name, v->value);

			value = v->value;
		} else {
			DEBUG(parser->pakfire, "Replacing %%{%s} with an empty string\n",
				variable);
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

static const char* pakfire_parser_get_raw(PakfireParser parser, const char* name) {
	struct pakfire_parser_declaration* d = pakfire_parser_get_declaration(parser, name);

	if (d)
		return d->value;

	// Search in parent parser if available
	if (parser->parent)
		return pakfire_parser_get_raw(parser->parent, name);

	return NULL;
}

PAKFIRE_EXPORT char* pakfire_parser_get(PakfireParser parser, const char* name) {
	const char* value = pakfire_parser_get_raw(parser, name);

	// Return NULL when nothing was found
	if (!value)
		return NULL;

	// Otherwise return the expanded value
	return pakfire_parser_expand(parser, value);
}

PAKFIRE_EXPORT PakfireParser pakfire_parser_merge(PakfireParser parser1, PakfireParser parser2) {
	DEBUG(parser1->pakfire, "Merging parsers %p and %p\n", parser1, parser2);

	// Do not try to merge a parser with itself
	if (parser1 == parser2)
		return parser1;

	for (unsigned int i = 0; i < parser2->num_declarations; i++) {
		struct pakfire_parser_declaration* d = parser2->declarations[i];
		if (!d)
			break;

		pakfire_parser_set_declaration(parser1, d->name, d->value);
	}

	return parser1;
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

PAKFIRE_EXPORT char* pakfire_parser_dump(PakfireParser parser) {
	char* s = NULL;

	for (unsigned int i = 0; i < parser->num_declarations; i++) {
		struct pakfire_parser_declaration* d = parser->declarations[i];

		if (d) {
			if (s)
				asprintf(&s, "%s%-24s = %s\n", s, d->name, d->value);
			else
				asprintf(&s, "%-24s = %s\n", d->name, d->value);
		}
	}

	return s;
}
