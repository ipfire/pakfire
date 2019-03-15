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

%option nounput noinput noyywrap yylineno

%{
#define YY_DECL int yylex()

int num_lines;

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

%%

#.*$			{ /* ignore comments */ }
{whitespace}	{}
\n				{ num_lines++; return NEWLINE; }

"=="			{ return EQUALS; }
"="				{ return ASSIGN; }
"+="			{ return APPEND; }

"if"			{ return IF; }
"def(ine)?"		{ return DEFINE; }
"end"			{ return END; }

{quoted_string}	{
					// Remove quotes
					size_t len = strlen(yytext);
					yytext[len-1] = '\0';

					yylval.string = pakfire_strdup(yytext + 1);
					return WORD;
				}

{word}			{
					yylval.string = pakfire_strdup(yytext);
					return WORD;
				}

%%
