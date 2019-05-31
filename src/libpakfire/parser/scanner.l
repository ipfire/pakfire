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

%option noinput noyywrap yylineno

%{
#define YY_DECL int yylex()

int num_lines;

#include <ctype.h>
#include <pakfire/parser.h>
#include <pakfire/util.h>
#include "grammar.h"

static char* find_name(const char* s, const char* prefix) {
	// Find the name of the package
	char* name = NULL;
	for (unsigned int i = strlen(s); i > 0; i--) {
		if (isspace(s[i]))
			break;

		name = s + i;
	}

	// New length
	size_t length = strlen(prefix) + strlen(name);

	// Allocate a new buffer and write the string into it
	char* buffer = pakfire_malloc(length + 1);
	snprintf(buffer, length + 1, "%s%s", prefix, name);

	return buffer;
}
%}

digit			[0-9]
letter			[A-Za-z]
underscore		_
special			[/\"'!@$%&*(){}+=:<>,;_\?\.\[\]\-\\\|]+
whitespace		([ \t])+

quoted_string	\"([^\"])*\"
word			({quoted_string}|({digit}|{letter}|{special})+)

/*
	Compatibility for the old python parser.

	We automatically prepend "define" in front of some keywords, because
	generally the language requires it.
*/
keywords		(description|{whitespace}(description|build(_cmds)?|files|filter_(provides|requires)|install(_cmds)?|prepare_cmds|provides|(pre)?requires|_posttrans))
package			{whitespace}package.*$
script			{whitespace}script.*$
template		{whitespace}template.*$


%s DEFINE

%%

#.*$			{ /* ignore comments */ }
{whitespace}	{}
\n				{ num_lines++; return T_EOL; }

<INITIAL>^{package} {
					char* buffer = find_name(yytext, "package:");

					// Put the whole string back onto the stack (backwards)
					for (int i = strlen(buffer) - 1; i >= 0; i--) {
						unput(buffer[i]);
					}

					pakfire_free(buffer);
				}

<INITIAL>^{template} {
					char* buffer = find_name(yytext, "template:");

					// Put the whole string back onto the stack (backwards)
					for (int i = strlen(buffer) - 1; i >= 0; i--) {
						unput(buffer[i]);
					}

					pakfire_free(buffer);
				}

<INITIAL>^{script} {
					char* buffer = find_name(yytext, "define script:");

					// Put the whole string back onto the stack (backwards)
					for (int i = strlen(buffer) - 1; i >= 0; i--) {
						unput(buffer[i]);
					}

					pakfire_free(buffer);
				}

<INITIAL>^{keywords}$ {
					// Determine the length of the string
					size_t length = strlen("define ") + yyleng;

					// Make a copy because unput touches yytext
					char* buffer = pakfire_malloc(length + 1);
					snprintf(buffer, length + 1, "define %s", yytext);

					// Put the whole string back onto the stack (backwards)
					for (int i = length - 1; i >= 0; i--) {
						unput(buffer[i]);
					}

					pakfire_free(buffer);
				}

<INITIAL>"=="	{ return T_EQUALS; }
<INITIAL>"="	{ return T_ASSIGN; }
<INITIAL>"+="	{ return T_APPEND; }

<INITIAL>"if"	{ return T_IF; }
<INITIAL>"else"	{ return T_ELSE; }

<INITIAL>"define" {
					BEGIN(DEFINE);
					return T_DEFINE;
				}
<INITIAL>"def"	{
					BEGIN(DEFINE);
					return T_DEFINE;
				}
<INITIAL>"end"	{
					return T_END;
				}

<DEFINE>"end"	{
					BEGIN(0);
					return T_END;
				}

{quoted_string}	{
					// Remove quotes
					size_t len = strlen(yytext);
					yytext[len-1] = '\0';

					yylval.string = pakfire_strdup(yytext + 1);
					return T_WORD;
				}

{word}			{
					yylval.string = pakfire_strdup(yytext);
					return T_WORD;
				}

%%
