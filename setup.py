
import os

from distutils.core import Extension, setup

from DistUtilsExtra.command import *

PAKFIRE_VERSION = "0.9.6"

_pakfire_module_files = [os.path.join("src", f) for f in os.listdir("src") if f.endswith(".c")]

# Update program version.
f = open("pakfire/__version__.py", "w")
f.write("# this file is autogenerated by setup.py\n")
f.write("PAKFIRE_VERSION = \"%s\"\n" % PAKFIRE_VERSION)
f.close()

setup(
	name = "pakfire",
	version = PAKFIRE_VERSION,
	description = "Pakfire - Package manager for IPFire.",
	author = "IPFire.org Team",
	author_email = "info@ipfire.org",
	url = "http://redmine.ipfire.org/projects/buildsystem3",
	packages = [
		"pakfire",
		"pakfire.packages",
		"pakfire.repository",
	],
	scripts = [
		"scripts/pakfire",
		"scripts/pakfire-build",
		"scripts/pakfire-server",
	],
	ext_modules = [
		Extension("pakfire._pakfire", _pakfire_module_files,
			extra_link_args = ["-lsolv", "-lsolvext"])
	],
	cmdclass = { "build" : build_extra.build_extra,
	             "build_i18n" :  build_i18n.build_i18n },
)
