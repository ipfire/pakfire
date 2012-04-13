#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
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
###############################################################################

import base
import client

from errors import *

Pakfire = base.Pakfire

def install(requires, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.install(requires)

def resolvdep(pkgs, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.resolvdep(pkgs)

def reinstall(pkgs, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.reinstall(pkgs)

def remove(what, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.remove(what)

def update(pkgs, check=False, excludes=None, allow_vendorchange=False, allow_archchange=False, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.update(pkgs, check=check, excludes=excludes,
		allow_vendorchange=allow_vendorchange, allow_archchange=allow_archchange)

def downgrade(pkgs, allow_vendorchange=False, allow_archchange=False, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.downgrade(pkgs,
		allow_vendorchange=allow_vendorchange, allow_archchange=allow_archchange)

def info(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.info(patterns)

def search(pattern, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.search(pattern)

def groupinstall(group, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.groupinstall(group)

def grouplist(group, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.grouplist(group)

def _build(pkg, resultdir, **kwargs):
	pakfire = Pakfire(mode="builder", **kwargs)

	return pakfire._build(pkg, resultdir, **kwargs)

def build(pkg, **kwargs):
	return Pakfire.build(pkg, **kwargs)

def shell(pkg, **kwargs):
	return Pakfire.shell(pkg, **kwargs)

def dist(pkg, resultdir, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.dist(pkg, resultdir)

def provides(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.provides(patterns)

def requires(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.requires(requires)

def repo_create(path, input_paths, name=None, key_id=None, type="binary", **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.repo_create(path, input_paths, name=name, key_id=key_id, type=type)

def repo_list(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.repo_list()

def clean_all(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.clean_all()

def check(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.check()

# Cache functions
def cache_create(**pakfire_args):
	return Pakfire.cache_create(**pakfire_args)


# Key functions.

def key_generate(realname, email, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.keyring.gen_key(realname, email)

def key_import(keyfile, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.keyring.import_key(keyfile)

def key_export(keyid, keyfile, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.keyring.export_key(keyid, keyfile)

def key_delete(keyid, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.keyring.delete_key(keyid)

def key_list(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.keyring.list_keys()
