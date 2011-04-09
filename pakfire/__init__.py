#!/usr/bin/python

import base
import builder
import depsolve
import packages
import transaction

from errors import *

Builder = builder.Builder
Pakfire = base.Pakfire

def install(requires, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	ds = depsolve.DependencySet(pakfire=pakfire)

	for req in requires:
		if isinstance(req, packages.BinaryPackage):
			ds.add_package(req)
		else:
			ds.add_requires(req)

	ds.resolve()
	ds.dump()

	ret = cli.ask_user(_("Is this okay?"))
	if not ret:
		return

	ts = transaction.Transaction(pakfire, ds)
	ts.run()

def remove(**pakfire_args):
	pass

def update(pkgs, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	ds = depsolve.DependencySet(pakfire=self)

	for pkg in ds.packages:
		# Skip unwanted packages (passed on command line)
		if pkgs and not pkg.name in pkgs:
			continue

		updates = pakfire.repos.get_by_name(pkg.name)
		updates = packages.PackageListing(updates)

		latest = updates.get_most_recent()

		# If the current package is already the latest
		# we skip it.
		if latest == pkg:
			continue

		# Otherwise we want to update the package.
		ds.add_package(latest)

	ds.resolve()
	ds.dump()

	ret = cli.ask_user(_("Is this okay?"))
	if not ret:
		return

	ts = transaction.Transaction(pakfire, ds)
	ts.run()

def info(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	pkgs = []

	for pattern in patterns:
		pkgs += pakfire.repos.get_by_glob(pattern)

	return packages.PackageListing(pkgs)

def search(pattern, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	# Do the search.
	pkgs = pakfire.repos.search(pattern)

	# Return the output as a package listing.
	return packages.PackageListing(pkgs)

def groupinstall(group, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	pkgs = grouplist(group, **pakfire_args)

	install(pkgs, **pakfire_args)

def grouplist(group, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	pkgs = pakfire.repos.get_by_group(group)

	pkgs = packages.PackageListing(pkgs)
	pkgs.unique()

	return [p.name for p in pkgs]

def build(pkg, distro_config=None, build_id=None, resultdirs=None, **pakfire_args):
	if not resultdirs:
		resultdirs = []

	b = Builder(pkg, distro_config, build_id=build_id, **pakfire_args)

	# Make shortcut to pakfire instance.
	p = b.pakfire

	# Always include local repository.
	resultdirs.append(p.repos.local_build.path)

	try:
		b.prepare()
		b.extract()
		b.build()
		b.install_test()

		# Copy-out all resultfiles
		for resultdir in resultdirs:
			if not resultdir:
				continue

			b.copy_result(resultdir)

	except BuildError:
		b.shell()

	finally:
		b.destroy()

def shell(pkg, distro_config=None, **pakfire_args):
	b = builder.Builder(pkg, distro_config, **pakfire_args)

	try:
		b.prepare()
		b.extract()
		b.shell()
	finally:
		b.destroy()

def dist(pkg, resultdirs=None, **pakfire_args):
	b = builder.Builder(pkg, **pakfire_args)
	p = b.pakfire

	if not resultdirs:
		resultdirs = []

	# Always include local repository
	resultdirs.append(p.repos.local_build.path)

	try:
		b.prepare()
		b.extract(build_deps=False)

		# Run the actual dist.
		b.dist()

		# Copy-out all resultfiles
		for resultdir in resultdirs:
			if not resultdir:
				continue

			b.copy_result(resultdir)
	finally:
		b.destroy()

def provides(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	pkgs = []
	for pattern in patterns:
		requires = depsolve.Requires(None, pattern)
		pkgs += pakfire.repos.get_by_provides(requires)

	pkgs = packages.PackageListing(pkgs)
	#pkgs.unique()

	return pkgs

def requires(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	pkgs = []
	for pattern in patterns:
		requires = depsolve.Requires(None, pattern)
		pkgs += pakfire.repos.get_by_requires(requires)

	pkgs = packages.PackageListing(pkgs)
	#pkgs.unique()

	return pkgs

def repo_create(path, input_paths, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	repo = repository.LocalBinaryRepository(
		pakfire,
		name="new",
		description="New repository.",
		path=path,
	)

	for input_path in input_paths:
		repo._collect_packages(input_path)

	repo.save()

def repo_list(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.repos.all
