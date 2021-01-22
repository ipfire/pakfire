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

LIBPAKFIRE_CURRENT=0
LIBPAKFIRE_REVISION=0
LIBPAKFIRE_AGE=0

libexecdir = $(libdir)/pakfire
pythondir  = $(pyexecdir)

configsdir = $(sysconfdir)/pakfire
configsdistrosdir = $(configsdir)/distros
macrosdir = $(prefix)/lib/pakfire/macros
qualityagentdir = $(prefix)/lib/quality-agent
scriptsdir = $(prefix)/lib/$(PACKAGE_NAME)

TEST_ROOTFS = $(abs_top_builddir)/tests/.root

CLEANFILES =
DISTCLEANFILES =
EXTRA_DIST =

AM_CPPFLAGS = \
	-include $(top_builddir)/config.h \
	-I $(top_srcdir)/include \
	$(OUR_CPPFLAGS)

AM_CFLAGS = $(OUR_CFLAGS) \
	-ffunction-sections \
	-fdata-sections

AM_LDFLAGS = $(OUR_LDFLAGS) \
	-Wl,--gc-sections \
	-Wl,--as-needed

AM_YFLAGS = -d

PAKFIRE_CPPFLAGS = -I$(top_srcdir)/src/libpakfire/include
PAKFIRE_LIBS     = libpakfire.la

check_PROGRAMS =
lib_LTLIBRARIES =
libexec_PROGRAMS =
noinst_LTLIBRARIES =
pkgpyexec_LTLIBRARIES =
pkginclude_HEADERS =

DISTCHECK_CONFIGURE_FLAGS = \
        --with-systemdsystemunitdir=$$dc_install_base/$(systemdsystemunitdir) \
	--enable-debug

@INTLTOOL_POLICY_RULE@

clean-local: clean-local-check

.PHONY: update-po
update-po: po/POTFILES.in
	$(MAKE) -C po update-po

po/POTFILES.in: Makefile
	find $(abs_srcdir)/src | \
		grep -E "\.(c|in|py)$$" | sed -e "s@$(abs_srcdir)/@@g" | LC_COLLATE=C sort > $@

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

# ------------------------------------------------------------------------------

pakfire_PYTHON = \
	src/pakfire/__init__.py \
	src/pakfire/__version__.py \
	src/pakfire/base.py \
	src/pakfire/builder.py \
	src/pakfire/cgroups.py \
	src/pakfire/client.py \
	src/pakfire/cli.py \
	src/pakfire/compress.py \
	src/pakfire/config.py \
	src/pakfire/constants.py \
	src/pakfire/daemon.py \
	src/pakfire/distro.py \
	src/pakfire/downloaders.py \
	src/pakfire/errors.py \
	src/pakfire/filelist.py \
	src/pakfire/http.py \
	src/pakfire/hub.py \
	src/pakfire/i18n.py \
	src/pakfire/logger.py \
	src/pakfire/progressbar.py \
	src/pakfire/shell.py \
	src/pakfire/system.py \
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
	src/pakfire/packages/tar.py

pakfire_packagesdir = $(pythondir)/pakfire/packages

# ------------------------------------------------------------------------------

pakfire_repository_PYTHON = \
	src/pakfire/repository/__init__.py \
	src/pakfire/repository/base.py \
	src/pakfire/repository/database.py \
	src/pakfire/repository/local.py \
	src/pakfire/repository/metadata.py \
	src/pakfire/repository/system.py

pakfire_repositorydir = $(pythondir)/pakfire/repository

# ------------------------------------------------------------------------------

pakfire_ui_PYTHON = \
	src/pakfire/ui/__init__.py \
	src/pakfire/ui/base.py \
	src/pakfire/ui/cli.py \
	src/pakfire/ui/helpers.py \
	src/pakfire/ui/progressbar.py

pakfire_uidir = $(pythondir)/pakfire/ui

# ------------------------------------------------------------------------------

pkgpyexec_LTLIBRARIES += \
	_pakfire.la

_pakfire_la_SOURCES = \
	src/_pakfire/_pakfiremodule.c \
	src/_pakfire/archive.c \
	src/_pakfire/archive.h \
	src/_pakfire/capabilities.c \
	src/_pakfire/capabilities.h \
	src/_pakfire/constants.h \
	src/_pakfire/errors.h \
	src/_pakfire/key.c \
	src/_pakfire/key.h \
	src/_pakfire/package.c \
	src/_pakfire/package.h \
	src/_pakfire/pakfire.c \
	src/_pakfire/pakfire.h \
	src/_pakfire/problem.c \
	src/_pakfire/problem.h \
	src/_pakfire/relation.c \
	src/_pakfire/relation.h \
	src/_pakfire/repo.c \
	src/_pakfire/repo.h \
	src/_pakfire/request.c \
	src/_pakfire/request.h \
	src/_pakfire/selector.c \
	src/_pakfire/selector.h \
	src/_pakfire/solution.c \
	src/_pakfire/solution.h \
	src/_pakfire/step.c \
	src/_pakfire/step.h \
	src/_pakfire/transaction.c \
	src/_pakfire/transaction.h \
	src/_pakfire/util.c \
	src/_pakfire/util.h

_pakfire_la_CPPFLAGS = \
	-include $(top_builddir)/config.h \
	$(PAKFIRE_CPPFLAGS)

_pakfire_la_CFLAGS = \
	$(AM_CFLAGS) \
	$(PYTHON_DEVEL_CFLAGS) \
	$(CAP_CFLAGS) \
	$(SOLV_CFLAGS) \
	-Wno-cast-function-type

_pakfire_la_LDFLAGS = \
	$(AM_LDFLAGS) \
	-shared \
	-module \
	-avoid-version

_pakfire_la_LIBADD = \
	$(PYTHON_DEVEL_LIBS) \
	$(PAKFIRE_LIBS) \
	$(CAP_LIBS) \
	$(SOLV_LIBS)

# ------------------------------------------------------------------------------

CLEANFILES += \
	src/libpakfire/grammar.c \
	src/libpakfire/grammar.h \
	src/libpakfire/scanner.c

noinst_LTLIBRARIES += \
	libpakfire-parser.la

libpakfire_parser_la_SOURCES = \
	src/libpakfire/parser/grammar.h \
	src/libpakfire/parser/grammar.y \
	src/libpakfire/parser/scanner.l

libpakfire_parser_la_CFLAGS = \
	$(AM_CFLAGS)

libpakfire_parser_la_CPPFLAGS = \
	$(AM_CPPFLAGS) \
	-I$(top_srcdir)/src/libpakfire/include \
	-include $(top_builddir)/config.h \
	-DPAKFIRE_PRIVATE

src/libpakfire/parser/scanner.c: src/libpakfire/parser/grammar.h

lib_LTLIBRARIES += \
	libpakfire.la

libpakfire_la_SOURCES = \
	src/libpakfire/arch.c \
	src/libpakfire/archive.c \
	src/libpakfire/db.c \
	src/libpakfire/errno.c \
	src/libpakfire/execute.c \
	src/libpakfire/file.c \
	src/libpakfire/filter.c \
	src/libpakfire/key.c \
	src/libpakfire/logging.c \
	src/libpakfire/package.c \
	src/libpakfire/packagelist.c \
	src/libpakfire/pakfire.c \
	src/libpakfire/parser.c \
	src/libpakfire/problem.c \
	src/libpakfire/relation.c \
	src/libpakfire/relationlist.c \
	src/libpakfire/repo.c \
	src/libpakfire/request.c \
	src/libpakfire/selector.c \
	src/libpakfire/solution.c \
	src/libpakfire/step.c \
	src/libpakfire/transaction.c \
	src/libpakfire/util.c

pkginclude_HEADERS += \
	src/libpakfire/include/pakfire/arch.h \
	src/libpakfire/include/pakfire/archive.h \
	src/libpakfire/include/pakfire/constants.h \
	src/libpakfire/include/pakfire/db.h \
	src/libpakfire/include/pakfire/errno.h \
	src/libpakfire/include/pakfire/execute.h \
	src/libpakfire/include/pakfire/file.h \
	src/libpakfire/include/pakfire/filter.h \
	src/libpakfire/include/pakfire/i18n.h \
	src/libpakfire/include/pakfire/key.h \
	src/libpakfire/include/pakfire/logging.h \
	src/libpakfire/include/pakfire/package.h \
	src/libpakfire/include/pakfire/packagelist.h \
	src/libpakfire/include/pakfire/pakfire.h \
	src/libpakfire/include/pakfire/parser.h \
	src/libpakfire/include/pakfire/private.h \
	src/libpakfire/include/pakfire/problem.h \
	src/libpakfire/include/pakfire/relation.h \
	src/libpakfire/include/pakfire/relationlist.h \
	src/libpakfire/include/pakfire/repo.h \
	src/libpakfire/include/pakfire/request.h \
	src/libpakfire/include/pakfire/selector.h \
	src/libpakfire/include/pakfire/solution.h \
	src/libpakfire/include/pakfire/step.h \
	src/libpakfire/include/pakfire/transaction.h \
	src/libpakfire/include/pakfire/types.h \
	src/libpakfire/include/pakfire/util.h

libpakfire_la_CFLAGS = \
	$(AM_CFLAGS) \
	-fvisibility=hidden \
	$(LIBGCRYPT_CFLAGS) \
	$(SQLITE3_CFLAGS)

libpakfire_la_CPPFLAGS = \
	$(AM_CPPFLAGS) \
	-I$(top_srcdir)/src/libpakfire/include \
	-include $(top_builddir)/config.h \
	-DPAKFIRE_PRIVATE

libpakfire_la_LDFLAGS = \
	$(AM_LDFLAGS) \
	-version-info $(LIBPAKFIRE_CURRENT):$(LIBPAKFIRE_REVISION):$(LIBPAKFIRE_AGE) \
	-Wl,--version-script=$(top_srcdir)/src/libpakfire/libpakfire.sym

libpakfire_la_LIBADD = \
	libpakfire-parser.la \
	$(ARCHIVE_LIBS) \
	$(GPGME_LIBS) \
	$(LIBGCRYPT_LIBS) \
	$(LZMA_LIBS) \
	$(SOLV_LIBS) \
	$(SQLITE3_LIBS)

libpakfire_la_DEPENDENCIES = \
	src/libpakfire/libpakfire.sym \
	libpakfire-parser.la

EXTRA_DIST += \
	src/libpakfire/libpakfire.sym

check_PROGRAMS += \
	tests/libpakfire/main \
	tests/libpakfire/arch \
	tests/libpakfire/archive \
	tests/libpakfire/db \
	tests/libpakfire/execute \
	tests/libpakfire/key \
	tests/libpakfire/makefile \
	tests/libpakfire/parser \
	tests/libpakfire/util

dist_tests_libpakfire_main_SOURCES = \
	tests/libpakfire/main.c

tests_libpakfire_main_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS) \
	-DTEST_ROOTFS=\"$(TEST_ROOTFS)\"

tests_libpakfire_main_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

tests_libpakfire_arch_SOURCES = \
	tests/libpakfire/arch.c

tests_libpakfire_arch_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS)

tests_libpakfire_arch_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

tests_libpakfire_archive_SOURCES = \
	tests/libpakfire/archive.c

tests_libpakfire_archive_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS)

tests_libpakfire_archive_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

tests_libpakfire_db_SOURCES = \
	tests/libpakfire/db.c

tests_libpakfire_db_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS)

tests_libpakfire_db_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

tests_libpakfire_execute_SOURCES = \
	tests/libpakfire/execute.c

tests_libpakfire_execute_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS)

tests_libpakfire_execute_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

tests_libpakfire_key_SOURCES = \
	tests/libpakfire/key.c \
	tests/libpakfire/key.h

tests_libpakfire_key_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS)

tests_libpakfire_key_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

dist_tests_libpakfire_makefile_SOURCES = \
	tests/libpakfire/makefile.c

tests_libpakfire_makefile_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS) \
	-DPAKFIRE_PRIVATE

tests_libpakfire_makefile_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

dist_tests_libpakfire_parser_SOURCES = \
	tests/libpakfire/parser.c

tests_libpakfire_parser_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS)

tests_libpakfire_parser_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

dist_tests_libpakfire_util_SOURCES = \
	tests/libpakfire/util.c

tests_libpakfire_util_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS)

tests_libpakfire_util_LDADD = \
	$(TESTSUITE_LDADD) \
	$(PAKFIRE_LIBS)

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

check_LTLIBRARIES = \
	tests/libtestsuite.la

tests_libtestsuite_la_SOURCES = \
	tests/testsuite.c \
	tests/testsuite.h

tests_libtestsuite_la_CPPFLAGS = \
	$(TESTSUITE_CPPFLAGS) \
	-DABS_TOP_SRCDIR=\"$(abs_top_srcdir)\" \
	-DTEST_ROOTFS=\"$(TEST_ROOTFS)\"

TESTSUITE_CPPFLAGS = \
	$(AM_CPPFLAGS) \
	$(PAKFIRE_CPPFLAGS)

TESTSUITE_LDADD = \
	tests/libtestsuite.la

TESTS_ENVIRONMENT = \
	PAKFIRE_LOG=debug \
	PYTHONPATH="$(top_srcdir)/.libs:$(top_srcdir)/src" \
	topdir="$(shell pwd)"

dist_check_SCRIPTS = \
	tests/python/cgroups.py \
	tests/python/execute.py \
	tests/python/test.py

TESTS = \
	$(check_PROGRAMS) \
	$(dist_check_SCRIPTS)

# Some test data to run tests
EXTRA_DIST += \
	tests/data/726D8B0B0889B04E.key \
	tests/data/beep-1.3-2.ip3.x86_64.pfm

.PHONY: clean-local-check
clean-local-check:
	-rm -rf $(TEST_ROOTFS)/*
