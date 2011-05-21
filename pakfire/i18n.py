#!/usr/bin/python

"""
	The translation process of all strings is done in here.
"""

import  gettext

"""
	A function that returnes the same string.
"""
N_ = lambda x: x

def _(singular, plural=None, n=None):
	"""
		A function that returnes the translation of a string if available.

		The language is taken from the system environment.
	"""
	if not plural is None:
		assert n is not None
		return gettext.ldngettext("pakfire", singular, plural, n)

	return gettext.ldgettext("pakfire", singular)
