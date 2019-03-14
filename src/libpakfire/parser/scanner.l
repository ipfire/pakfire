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
special			[/'!@$%&*(){}+=:<>,;?_\.\[\]\-\\]+
whitespace		([ \t])+

word			({digit}|{letter}|{special})+

%%

#.*$			{ /* ignore comments */ }
{whitespace}	{ return WHITESPACE; }
\n				{ num_lines++; return NEWLINE; }

"=="			{ return EQUALS; }
"="				{ return ASSIGN; }
"+="			{ return APPEND; }

"if"			{ return IF; }
"define"		{ return DEFINE; }
"def"			{ return DEFINE; }
"end"			{ return END; }

{word}			{
					yylval.string = pakfire_strdup(yytext);
					return WORD;
				}

%%
