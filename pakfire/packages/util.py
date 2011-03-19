#!/usr/bin/python

from __future__ import division

import hashlib
import re

from pakfire.constants import *

def version_compare_epoch(e1, e2):
	# If either e1 or e2 is None, we cannot say anything
	if None in (e1, e2):
		return 0

	return cmp(e1, e2)

def version_compare_version(v1, v2):
	return cmp(v1, v2)

def version_compare_release(r1, r2):
	# If either e1 or e2 is None, we cannot say anything
	if None in (r1, r2):
		return 0

	if "." in r1:
		r1, d1 = r1.split(".", 1)

	if "." in r2:
		r2, d2 = r2.split(".", 1)

	# Compare the distribution tag at first.
	ret = cmp(d1, d2)

	if not ret == 0:
		return ret

	r1 = int(r1)
	r2 = int(r2)

	return cmp(r1, r2)

def version_compare((e1, v1, r1), (e2, v2, r2)):
	ret = version_compare_epoch(e1, e2)
	if not ret == 0:
		return ret

	ret = version_compare_version(v1, v2)
	if not ret == 0:
		return ret

	return version_compare_release(r1, r2)

def text_wrap(s, length=65):
	t = []
	s = s.split()

	l = []
	for word in s:
		l.append(word)

		if len(" ".join(l)) >= length:
			t.append(l)
			l = []

	if l:
		t.append(l)

	return [" ".join(l) for l in t]

def format_size(s):
	units = ("B", "k", "M", "G", "T")
	unit = 0

	while s >= 1024 and unit < len(units):
		s /= 1024
		unit += 1

	return "%d%s" % (int(s), units[unit])

def calc_hash1(filename=None, data=None):
	h = hashlib.sha1()

	if filename:
		f = open(filename)
		buf = f.read(BUFFER_SIZE)
		while buf:
			h.update(buf)
			buf = f.read(BUFFER_SIZE)

		f.close()

	elif data:
		h.update(data)

	return h.hexdigest()

def parse_pkg_expr(s):
	# Possible formats:
	#   gcc=4.0.0
	#   gcc=4.0.0-1
	#   gcc=4.0.0-1.ip3
	#   gcc=0:4.0.0-1
	#   gcc=0:4.0.0-1.ip3
	#   gcc>=...
	#   gcc>...
	#   gcc<...
	#   gcc<=...

	(name, exp, epoch, version, release) = (None, None, None, None, None)

	m = re.match(r"([A-Za-z0-9\-\+]+)(=|\<|\>|\>=|\<=)([0-9]+\:)?([0-9A-Za-z\.]+)-?([0-9]+\.?[a-z0-9]+|[0-9]+)?", s)

	if m:
		(name, exp, epoch, version, release) = m.groups()

		# Remove : from epoch and convert to int
		if epoch:
			epoch = epoch.replace(":", "")
			epoch = int(epoch)

	return (exp, name, epoch, version, release)

def test_parse_pkg_expr():
	strings = (
		"gcc=4.0.0",
		"gcc=4.0.0-1",
		"gcc=4.0.0-1.ip3",
		"gcc=0:4.0.0-1",
		"gcc=0:4.0.0-1.ip3",
		"gcc>=4.0.0-1",
		"gcc>4.0.0-1",
		"gcc<4.0.0-1",
		"gcc<=4.0.0-1",
	)

	for s in strings:
		print s, parse_pkg_expr(s)

def parse_virtual_expr(s):
	# pkgconfig(bla)=1.2.3

	(type, name, exp, version) = (None, None, None, None)

	m = re.match(r"^([A-Za-z0-9]+)\(([A-Za-z0-9\.\-\+:]+)\)?(=|\<|\>|\>=|\<=)?([A-Za-z0-9\.\-]+)?", s)

	if m:
		(type, name, exp, version) = m.groups()

	return (type, exp, name, version)

def test_parse_virtual_expr():
	strings = (
		"pkgconfig(libxml-2.0)",
		"pkgconfig(libxml-2.0)=1.2.3",
		"pkgconfig(libxml-2.0)>=1.2.3",
	)

	for s in strings:
		print s, parse_virtual_expr(s)

if __name__ == "__main__":
	test_parse_pkg_expr()
	test_parse_virtual_expr()
