#!/usr/bin/python

import os.path

PAKFIRE_VERSION = "testing"

SYSCONFDIR = os.path.join(os.path.dirname(__file__), "..", "examples")
if not os.path.exists(SYSCONFDIR):
	SYSCONFDIR = "/etc"

CONFIG_DIR = os.path.join(SYSCONFDIR, "pakfire.repos.d")
CONFIG_FILE = os.path.join(SYSCONFDIR, "pakfire.conf")

CACHE_DIR = "/var/cache/pakfire"
CCACHE_CACHE_DIR = os.path.join(CACHE_DIR, "ccache")
REPO_CACHE_DIR = os.path.join(CACHE_DIR, "repos")

LOCAL_BUILD_REPO_PATH = "/var/lib/pakfire/local"

PACKAGES_DB_DIR = "var/lib/pakfire"
PACKAGES_DB = os.path.join(PACKAGES_DB_DIR, "packages.db")
REPOSITORY_DB = "index.db"

BUFFER_SIZE = 1024**2

METADATA_FORMAT = 0
METADATA_DOWNLOAD_LIMIT = 1024**2
METADATA_DOWNLOAD_PATH  = "repodata"
METADATA_DOWNLOAD_FILE  = "repomd.json"
METADATA_DATABASE_FILE  = "packages.db"

PACKAGE_FORMAT = 0
PACKAGE_EXTENSION = "pfm"
MAKEFILE_EXTENSION = "nm"

PACKAGE_FILENAME_FMT = "%(name)s-%(version)s-%(release)s.%(arch)s.%(ext)s"

BUILD_PACKAGES = ["build-essentials",]
SHELL_PACKAGES = ["less", "pakfire", "vim",]
BUILD_ROOT = "/var/lib/pakfire/build"

SOURCE_DOWNLOAD_URL = "http://source.ipfire.org/source-3.x/"
SOURCE_CACHE_DIR = os.path.join(CACHE_DIR, "sources")

TIME_10M = 10
TIME_24H = 60*24

SOURCE_PACKAGE_META = """\

PKG_NAME="%(PKG_NAME)s"

"""

BINARY_PACKAGE_META = """\
### %(name)s package

VERSION="%(package_format)s"

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

PKG_GROUP="%(group)s"
PKG_ARCH="%(arch)s"

PKG_MAINTAINER="%(maintainer)s"
PKG_LICENSE="%(license)s"
PKG_URL="%(url)s"

PKG_SUMMARY="%(summary)s"
PKG_DESCRIPTION="%(description)s"

# Dependency info
PKG_REQUIRES="%(requires)s"
PKG_PROVIDES="%(provides)s"

PKG_PAYLOAD_COMP="%(payload_comp)s"
PKG_PAYLOAD_SIZE="107869"

"""
