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
keywords		(description|{whitespace}(build(_cmds)?|files|install(_cmds)?|prepare_cmds|provides|(pre)?requires|_posttrans))
template		{whitespace}template.*$

%s DEFINE

%%

#.*$			{ /* ignore comments */ }
{whitespace}	{}
\n				{ num_lines++; return T_EOL; }

<INITIAL>^{template} {
					// Find the name of the template
					char* name = NULL;
					for (unsigned int i = yyleng; i > 0; i--) {
						if (isspace(yytext[i]))
							break;

						name = yytext + i;
					}

					size_t length = strlen("template:") + strlen(name);

					char* buffer = pakfire_malloc(length + 1);
					snprintf(buffer, length + 1, "template:%s", name);

					// Put the whole string back onto the stack (backwards)
					for (int i = length - 1; i >= 0; i--) {
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
