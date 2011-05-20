
from distutils.core import setup

from DistUtilsExtra.command import *

from pakfire.constants import PAKFIRE_VERSION

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
		"scripts/pakfire-repo",
		"scripts/pakfire-server",
	],
	cmdclass = { "build" : build_extra.build_extra,
	             "build_i18n" :  build_i18n.build_i18n },
)
