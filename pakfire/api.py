#!/usr/bin/python

import base

from errors import *

Pakfire = base.Pakfire

def install(requires, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.install(requires)

def localinstall(files, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.localinstall(files)

def remove(what, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.remove(what)

def update(pkgs, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.update(pkgs)

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

def build(pkg, **kwargs):
	return Pakfire.build(pkg, **kwargs)

def shell(pkg, **kwargs):
	return Pakfire.shell(pkg, **kwargs)

def dist(pkgs, **kwargs):
	return Pakfire.dist(pkgs, **kwargs)

def provides(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.provides(patterns)

def requires(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.requires(requires)

def repo_create(path, input_paths, type="binary", **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.repo_create(path, input_paths, type=type)

def repo_list(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.repo_list()

def clean_all(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.clean_all()

def check(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.check()
