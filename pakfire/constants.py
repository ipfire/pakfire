#!/usr/bin/python

import os.path

from errors import *

from __version__ import PAKFIRE_VERSION

SYSCONFDIR = "/etc"

CONFIG_DIR = os.path.join(SYSCONFDIR, "pakfire.repos.d")
CONFIG_FILE = os.path.join(SYSCONFDIR, "pakfire.conf")

CACHE_DIR = "/var/cache/pakfire"
CCACHE_CACHE_DIR = os.path.join(CACHE_DIR, "ccache")
REPO_CACHE_DIR = os.path.join(CACHE_DIR, "repos")

LOCAL_BUILD_REPO_PATH = "/var/lib/pakfire/local"
LOCAL_TMP_PATH = "/var/tmp/pakfire"

PACKAGES_DB_DIR = "var/lib/pakfire"
PACKAGES_DB = os.path.join(PACKAGES_DB_DIR, "packages.db")
REPOSITORY_DB = "index.db"

BUFFER_SIZE = 102400

MIRRORLIST_MAXSIZE = 1024**2

METADATA_FORMAT = 0
METADATA_DOWNLOAD_LIMIT = 1024**2
METADATA_DOWNLOAD_PATH  = "repodata"
METADATA_DOWNLOAD_FILE  = "repomd.json"
METADATA_DATABASE_FILE  = "packages.solv"

PACKAGE_FORMAT = 0
PACKAGE_EXTENSION = "pfm"
MAKEFILE_EXTENSION = "nm"

PACKAGE_FILENAME_FMT = "%(name)s-%(version)s-%(release)s.%(arch)s.%(ext)s"

BUILD_PACKAGES = ["build-essentials>=2:1.0-1.ip3",]
SHELL_PACKAGES = ["elinks", "less", "pakfire", "vim",]
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
ORPHAN_DIRECTORIES.sort(cmp=lambda x,y: cmp(len(x), len(y)), reverse=True)

BINARY_PACKAGE_META = SOURCE_PACKAGE_META = """\
### %(name)s package

VERSION="%(package_format)s"
TYPE="%(package_type)s"

# Build information
BUILD_DATE="%(build_date)s"
BUILD_HOST="%(build_host)s"
BUILD_ID="%(build_id)s"
BUILD_TIME="%(build_time)s"

# Distribution information
DISTRO_NAME="%(distro_name)s"
DISTRO_RELEASE="%(distro_release)s"
DISTRO_VENDOR="%(distro_vendor)s"

# Package information
PKG_NAME="%(name)s"
PKG_VER="%(version)s"
PKG_REL="%(release)s"
PKG_EPOCH="%(epoch)s"
PKG_UUID="%(package_uuid)s"

PKG_GROUPS="%(groups)s"
PKG_ARCH="%(arch)s"

PKG_MAINTAINER="%(maintainer)s"
PKG_LICENSE="%(license)s"
PKG_URL="%(url)s"

PKG_SUMMARY="%(summary)s"
PKG_DESCRIPTION="%(description)s"

# Dependency info
PKG_PREREQUIRES="%(prerequires)s"
PKG_REQUIRES="%(requires)s"
PKG_PROVIDES="%(provides)s"
PKG_CONFLICTS="%(conflicts)s"
PKG_OBSOLETES="%(obsoletes)s"

PKG_PAYLOAD_COMP="%(payload_comp)s"
PKG_PAYLOAD_HASH1="%(payload_hash1)s"

"""

# XXX make this configurable in pakfire.conf
PAKFIRE_MULTIINSTALL = ["kernel",]
