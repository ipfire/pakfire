#!/usr/bin/python

"""
	The translation process of all strings is done in here.
"""

import  gettext

"""
	A function that returnes the same string.
"""
N_ = lambda x: x


"""
	A function that returnes the translation of a string if available.

	The language is taken from the system environment.
"""
# Enable this to have translation in the development environment.
# gettext.bindtextdomain("pakfire", "build/mo")

_ = lambda x: gettext.ldgettext("pakfire", x)

