###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2013 Pakfire development team                                 #
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

ACLOCAL_AMFLAGS = -I m4 ${ACLOCAL_FLAGS}
AM_MAKEFLAGS = --no-print-directory
AUTOMAKE_OPTIONS = color-tests

# remove target it the command fails
.DELETE_ON_ERROR:

# keep itermediate files
.SECONDARY:

SUBDIRS = . po

libexecdir = $(libdir)/pakfire
pythondir  = $(pyexecdir)

configsdir = $(sysconfdir)/pakfire
configsdistrosdir = $(configsdir)/distros
macrosdir = $(prefix)/lib/pakfire/macros
qualityagentdir = $(prefix)/lib/quality-agent
scriptsdir = $(prefix)/lib/$(PACKAGE_NAME)

CLEANFILES =
DISTCLEANFILES =
EXTRA_DIST =

AM_CPPFLAGS = \
	-include $(top_builddir)/config.h \
	-I $(top_srcdir)/include \
	$(OUR_CPPFLAGS)

AM_CFLAGS = $(OUR_CFLAGS)
AM_LDFLAGS = $(OUR_LDFLAGS)

lib_LTLIBRARIES =
libexec_PROGRAMS =
pkgpyexec_LTLIBRARIES =

DISTCHECK_CONFIGURE_FLAGS = \
        --with-systemdsystemunitdir=$$dc_install_base/$(systemdsystemunitdir)

@INTLTOOL_POLICY_RULE@

.PHONY: update-po
update-po:
	$(MAKE) -C po update-po

# ------------------------------------------------------------------------------

dist_doc_DATA = \
	COPYING \
	I18N \
	README

# ------------------------------------------------------------------------------

dist_bin_SCRIPTS = \
	src/scripts/pakfire

install-exec-local:
	$(MKDIR_P) $(DESTDIR)/$(bindir)
	cd $(DESTDIR)/$(bindir) && \
		$(LN_S) -vf pakfire pakfire-builder && \
		$(LN_S) -vf pakfire pakfire-client && \
		$(LN_S) -vf pakfire pakfire-daemon && \
		$(LN_S) -vf pakfire pakfire-key

	$(MKDIR_P) $(DESTDIR)/$(scriptsdir)
	cd $(DESTDIR)/$(scriptsdir) && \
		$(LN_S) -vf ../../bin/pakfire builder

# ------------------------------------------------------------------------------

pakfire_PYTHON = \
	src/pakfire/__init__.py \
	src/pakfire/__version__.py \
	src/pakfire/actions.py \
	src/pakfire/base.py \
	src/pakfire/builder.py \
	src/pakfire/cgroup.py \
	src/pakfire/client.py \
	src/pakfire/cli.py \
	src/pakfire/compress.py \
	src/pakfire/config.py \
	src/pakfire/constants.py \
	src/pakfire/daemon.py \
	src/pakfire/distro.py \
	src/pakfire/downloader.py \
	src/pakfire/errors.py \
	src/pakfire/filelist.py \
	src/pakfire/i18n.py \
	src/pakfire/keyring.py \
	src/pakfire/logger.py \
	src/pakfire/lzma.py \
	src/pakfire/progressbar.py \
	src/pakfire/satsolver.py \
	src/pakfire/server.py \
	src/pakfire/shell.py \
	src/pakfire/system.py \
	src/pakfire/transaction.py \
	src/pakfire/transport.py \
	src/pakfire/util.py

pakfiredir = $(pythondir)/pakfire

# ------------------------------------------------------------------------------

pakfire_packages_PYTHON = \
	src/pakfire/packages/__init__.py \
	src/pakfire/packages/base.py \
	src/pakfire/packages/file.py \
	src/pakfire/packages/installed.py \
	src/pakfire/packages/lexer.py \
	src/pakfire/packages/make.py \
	src/pakfire/packages/packager.py \
	src/pakfire/packages/solv.py \
	src/pakfire/packages/tar.py

pakfire_packagesdir = $(pythondir)/pakfire/packages

# ------------------------------------------------------------------------------

pakfire_repository_PYTHON = \
	src/pakfire/repository/__init__.py \
	src/pakfire/repository/base.py \
	src/pakfire/repository/cache.py \
	src/pakfire/repository/database.py \
	src/pakfire/repository/index.py \
	src/pakfire/repository/local.py \
	src/pakfire/repository/metadata.py \
	src/pakfire/repository/remote.py \
	src/pakfire/repository/system.py

pakfire_repositorydir = $(pythondir)/pakfire/repository

# ------------------------------------------------------------------------------

pkgpyexec_LTLIBRARIES += \
	_lzma.la

_lzma_la_SOURCES = \
	src/_lzma/_lzmamodule.c

_lzma_la_CFLAGS = \
	$(AM_CFLAGS) \
	$(PYTHON_DEVEL_CFLAGS) \
	$(LZMA_CFLAGS)

_lzma_la_LDFLAGS = \
	$(AM_LDFLAGS) \
	-shared \
	-module \
	-avoid-version

_lzma_la_LIBADD = \
	$(PYTHON_DEVEL_LIBS) \
	$(LZMA_LIBS)

# ------------------------------------------------------------------------------

pkgpyexec_LTLIBRARIES += \
	_pakfire.la

_pakfire_la_SOURCES = \
	src/_pakfire/_pakfiremodule.c \
	src/_pakfire/capabilities.c \
	src/_pakfire/capabilities.h \
	src/_pakfire/constants.h \
	src/_pakfire/pool.c \
	src/_pakfire/pool.h \
	src/_pakfire/problem.c \
	src/_pakfire/problem.h \
	src/_pakfire/relation.c \
	src/_pakfire/relation.h \
	src/_pakfire/repo.c \
	src/_pakfire/repo.h \
	src/_pakfire/request.c \
	src/_pakfire/request.h \
	src/_pakfire/solution.c \
	src/_pakfire/solution.h \
	src/_pakfire/solvable.c \
	src/_pakfire/solvable.h \
	src/_pakfire/solver.c \
	src/_pakfire/solver.h \
	src/_pakfire/step.c \
	src/_pakfire/step.h \
	src/_pakfire/transaction.c \
	src/_pakfire/transaction.h \
	src/_pakfire/util.c \
	src/_pakfire/util.h

_pakfire_la_CFLAGS = \
	$(AM_CFLAGS) \
	$(PYTHON_DEVEL_CFLAGS) \
	$(CAP_CFLAGS) \
	$(SOLV_CFLAGS)

_pakfire_la_LDFLAGS = \
	$(AM_LDFLAGS) \
	-shared \
	-module \
	-avoid-version

_pakfire_la_LIBADD = \
	$(PYTHON_DEVEL_LIBS) \
	$(CAP_LIBS) \
	$(SOLV_LIBS)

# ------------------------------------------------------------------------------

lib_LTLIBRARIES += \
	libpakfire_preload.la

libpakfire_preload_la_SOURCES = \
	src/libpakfire_preload/uname.c

libpakfire_preload_la_LDFLAGS = \
	$(AM_LDFLAGS) \
	-shared \
	-module \
	-avoid-version

libpakfire_preload_la_LIBADD = \
	$(DL_LIBS)

# ------------------------------------------------------------------------------

libexec_PROGRAMS += \
	debugedit

debugedit_SOURCES = \
	src/debugedit/debugedit.c \
	src/debugedit/hashtab.c \
	src/debugedit/hashtab.h \
	src/debugedit/rpmiotypes.h \
	src/debugedit/rpmsw.h \
	src/debugedit/rpmtag.h

debugedit_LDADD = \
	$(AM_CFLAGS) \
	$(BEECRYPT_LIBS) \
	$(ELF_LIBS) \
	$(POPT_LIBS)

# ------------------------------------------------------------------------------

scripts_SCRIPTS = \
	src/scripts/extract-debuginfo \
	src/scripts/quality-agent

EXTRA_DIST += \
	src/scripts/extract-debuginfo.in \
	src/scripts/quality-agent.in

CLEANFILES += \
	src/scripts/extract-debuginfo \
	src/scripts/quality-agent

dist_scripts_SCRIPTS = \
	src/scripts/chroot-shell \
	src/scripts/cleanup \
	src/scripts/compress-man-pages \
	src/scripts/find-common \
	src/scripts/find-prerequires \
	src/scripts/find-provides \
	src/scripts/find-requires \
	src/scripts/patch \
	src/scripts/perl.prov \
	src/scripts/perl.req \
	src/scripts/py-compile \
	src/scripts/remove-static-libs

dist_scripts_DATA = \
	src/scripts/functions-common \
	src/scripts/functions-constants \
	src/scripts/functions-directories \
	src/scripts/functions-files \
	src/scripts/functions-lists \
	src/scripts/functions-logging

# ------------------------------------------------------------------------------

dist_qualityagent_SCRIPTS = \
	src/quality-agent/001-include-files \
	src/quality-agent/001-remove-info-files \
	src/quality-agent/001-unsafe-files \
	src/quality-agent/002-bad-symlinks \
	src/quality-agent/003-libs-location \
	src/quality-agent/050-canary \
	src/quality-agent/050-execstacks \
	src/quality-agent/050-invalid-interpreters \
	src/quality-agent/050-libs-needed \
	src/quality-agent/050-libs-soname \
	src/quality-agent/050-libs-x86_64 \
	src/quality-agent/050-nx \
	src/quality-agent/050-relro \
	src/quality-agent/050-rpaths \
	src/quality-agent/095-directory-layout

dist_qualityagent_DATA = \
	src/quality-agent/qa-include

# ------------------------------------------------------------------------------

dist_macros_DATA = \
	macros/arch.macro \
	macros/build.macro \
	macros/cflags.macro \
	macros/constants.macro \
	macros/package-default.macro \
	macros/perl.macro \
	macros/python.macro \
	macros/quality-agent.macro \
	macros/systemd.macro \
	macros/templates.macro

# ------------------------------------------------------------------------------

if HAVE_SYSTEMD
systemdsystemunit_DATA = \
	src/systemd/pakfire-daemon.service

EXTRA_DIST += \
	src/systemd/pakfire-daemon.service.in

CLEANFILES += \
	src/systemd/pakfire-daemon.service
endif

# ------------------------------------------------------------------------------

dist_configs_DATA = \
	contrib/config/builder.conf \
	contrib/config/client.conf \
	contrib/config/daemon.conf \
	contrib/config/general.conf

dist_configsdistros_DATA = \
	contrib/config/distros/ipfire3.conf

# ------------------------------------------------------------------------------

substitutions = \
       '|PACKAGE_NAME=$(PACKAGE_NAME)|' \
       '|PACKAGE_VERSION=$(PACKAGE_VERSION)|' \
       '|bindir=$(bindir)|' \
       '|libexecdir=$(libexecdir)|' \
       '|qualityagentdir=$(qualityagentdir)|'

SED_PROCESS = \
	$(AM_V_GEN)$(MKDIR_P) $(dir $@) && \
	$(SED) $(subst '|,-e 's|@,$(subst =,\@|,$(subst |',|g',$(substitutions)))) \
		< $< > $@

src/scripts/%: src/scripts/%.in Makefile
	$(SED_PROCESS)

src/systemd/%: src/systemd/%.in Makefile
	$(SED_PROCESS)

# - testsuite ------------------------------------------------------------------

TESTS_ENVIRONMENT = \
	PYTHONPATH="$(top_srcdir)/.libs:$(top_srcdir)/src" \
	topdir="$(shell pwd)"

dist_check_SCRIPTS = \
	tests/module-load.py

TESTS = \
	$(dist_check_SCRTIPS)
