
from distutils.core import setup

from DistUtilsExtra.command import *

setup(
	name = "pakfire",
	version = "0.0.1",
	description = "Pakfire - Package manager for IPFire.",
	author = "IPFire.org Team",
	author_email = "info@ipfire.org",
	url = "http://redmine.ipfire.org/projects/buildsystem3",
	packages = ["pakfire"],
	scripts = ["scripts/pakfire", "scripts/pakfire-build"],
	cmdclass = { "build" : build_extra.build_extra,
	             "build_i18n" :  build_i18n.build_i18n },
)
