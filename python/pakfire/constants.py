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

import os.path

from errors import *

from __version__ import PAKFIRE_VERSION

PAKFIRE_LEAST_COMPATIBLE_VERSION = PAKFIRE_VERSION

SYSCONFDIR = "/etc"
SCRIPT_DIR = "/usr/lib/pakfire"

CONFIG_DIR = os.path.join(SYSCONFDIR, "pakfire.repos.d")
CONFIG_DIR_EXT = ".repo"
CONFIG_FILE = os.path.join(SYSCONFDIR, "pakfire.conf")

CACHE_DIR = "/var/cache/pakfire"
CCACHE_CACHE_DIR = os.path.join(CACHE_DIR, "ccache")
CACHE_ENVIRON_DIR = os.path.join(CACHE_DIR, "environments")
REPO_CACHE_DIR = os.path.join(CACHE_DIR, "repos")

LOCAL_BUILD_REPO_PATH = "/var/lib/pakfire/local"
LOCAL_TMP_PATH = "/var/tmp"

PACKAGES_DB_DIR = "var/lib/pakfire"
PACKAGES_DB = os.path.join(PACKAGES_DB_DIR, "packages.db")
PACKAGES_SOLV = os.path.join(PACKAGES_DB_DIR, "packages.solv")
REPOSITORY_DB = "index.db"

BUFFER_SIZE = 102400

MIRRORLIST_MAXSIZE = 1024**2

MACRO_FILE_DIR = "/usr/lib/pakfire/macros"
MACRO_FILES = \
	(os.path.join(MACRO_FILE_DIR, f) for f in sorted(os.listdir(MACRO_FILE_DIR)) if f.endswith(".macro"))

METADATA_FORMAT = 0
METADATA_DOWNLOAD_LIMIT = 1024**2
METADATA_DOWNLOAD_PATH  = "repodata"
METADATA_DOWNLOAD_FILE  = "repomd.json"
METADATA_DATABASE_FILE  = "packages.solv"

PACKAGE_FORMAT = 3
# XXX implement this properly
PACKAGE_FORMATS_SUPPORTED = [0, 1, 2, 3]
PACKAGE_EXTENSION = "pfm"
MAKEFILE_EXTENSION = "nm"

DATABASE_FORMAT = 3
DATABASE_FORMATS_SUPPORTED = [0, 1, 2, 3]

PACKAGE_FILENAME_FMT = "%(name)s-%(version)s-%(release)s.%(arch)s.%(ext)s"

BUILD_PACKAGES = [
	"@Build",
	"pakfire-build>=%s" % PAKFIRE_LEAST_COMPATIBLE_VERSION,
]

# A script that is called, when a user is dropped to a chroot shell.
SHELL_SCRIPT = "/usr/lib/pakfire/chroot-shell"
SHELL_PACKAGES = ["elinks", "less", "vim", SHELL_SCRIPT,]
BUILD_ROOT = "/var/lib/pakfire/build"

SOURCE_DOWNLOAD_URL = "http://source.ipfire.org/source-3.x/"
SOURCE_CACHE_DIR = os.path.join(CACHE_DIR, "sources")

TIME_10M = 10
TIME_24H = 60*24

ORPHAN_DIRECTORIES = [
	"lib", "lib64", "usr/lib", "usr/lib64", "libexec", "usr/libexec",
	"bin", "sbin", "usr/bin", "usr/sbin", "usr/include", "usr/share",
	"usr/share/man", "usr/share/man/man0", "usr/share/man/man1",
	"usr/share/man/man2", "usr/share/man/man3", "usr/share/man/man4",
	"usr/share/man/man5", "usr/share/man/man6", "usr/share/man/man7",
	"usr/share/man/man8", "usr/share/man/man9", "usr/lib/pkgconfig",
]
for i in ORPHAN_DIRECTORIES:
	i = os.path.dirname(i)

	if not i or i in ORPHAN_DIRECTORIES:
		continue

	ORPHAN_DIRECTORIES.append(i)

ORPHAN_DIRECTORIES.sort(cmp=lambda x,y: cmp(len(x), len(y)), reverse=True)

PACKAGE_INFO = """\
# Pakfire %(pakfire_version)s

# Package information
package
	name        = %(name)s
	version     = %(version)s
	release     = %(release)s
	epoch       = %(epoch)s
	arch        = %(arch)s

	uuid        = %(uuid)s
	groups      = %(groups)s
	maintainer  = %(maintainer)s
	url         = %(url)s
	license     = %(license)s

	summary     = %(summary)s

	def description
%(description)s
	end

	type        = %(type)s
	size        = %(inst_size)d
end

# Build information
build
	host        = %(build_host)s
	id          = %(build_id)s
	time        = %(build_time)d
end

# Distribution information
distribution
	name        = %(distro_name)s
	release     = %(distro_release)s
	vendor      = %(distro_vendor)s
	maintainer  = %(distro_maintainer)s
end

# Dependency information
dependencies
	def prerequires
%(prerequires)s
	end

	def requires
%(requires)s
	end

	def provides
%(provides)s
	end

	def conflicts
%(conflicts)s
	end

	def obsoletes
%(obsoletes)s
	end
end

# EOF
"""
PACKAGE_INFO_DESCRIPTION_LINE = PACKAGE_INFO_DEPENDENCY_LINE = "\t\t%s"

# XXX make this configurable in pakfire.conf
PAKFIRE_MULTIINSTALL = ["kernel", "kernel-PAE",]

SCRIPTLET_INTERPRETER = "/bin/sh"
SCRIPTLET_TIMEOUT = 60 * 15

SCRIPTS = (
	"prein",
	"postin",
	"preun",
	"postun",
	"preup",
	"postup",
	"posttransin",
	"posttransun",
	"posttransup",
)

LDCONFIG = "/sbin/ldconfig"

CONFIG_FILE_SUFFIX_NEW  = ".paknew"
CONFIG_FILE_SUFFIX_SAVE = ".paksave"
