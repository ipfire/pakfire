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

AC_PREREQ([2.64])

AC_INIT([pakfire],
	[0.9.27],
	[info@ipfire.org],
	[pakfire],
	[http://git.ipfire.org/?p=pakfire.git;a=summary])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_HEADERS([config.h])
AC_CONFIG_AUX_DIR([build-aux])

AC_USE_SYSTEM_EXTENSIONS
AC_SYS_LARGEFILE
AC_PREFIX_DEFAULT([/usr])

AM_INIT_AUTOMAKE([
	foreign
	1.11
	-Wall
	-Wno-portability
	silent-rules
	tar-pax
	subdir-objects
])
AM_SILENT_RULES([yes])
LT_PREREQ(2.2)
LT_INIT([disable-static])

IT_PROG_INTLTOOL([0.40.0])

XGETTEXT="${XGETTEXT} --keyword=_:1,2 --keyword=N_:1,2 --no-location"

GETTEXT_PACKAGE=pakfire
AC_SUBST(GETTEXT_PACKAGE)

AC_PROG_LN_S
AC_PROG_MKDIR_P
AC_PROG_SED

AC_ARG_ENABLE([debug],
	AS_HELP_STRING([--enable-debug], [enable debug messages @<:@default=disabled@:>@]),
	[], [enable_debug=no])
AS_IF([test "x$enable_debug" = "xyes"], [
	AC_DEFINE(ENABLE_DEBUG, [1], [Debug messages.])
])

# pkg-config
PKG_PROG_PKG_CONFIG
# This makes sure pkg.m4 is available.
m4_pattern_forbid([^_?PKG_[A-Z_]+$],[*** pkg.m4 missing, please install pkg-config])

# C Compiler
AC_PROG_CC
AC_PROG_CC_C99
AC_PROG_CC_C_O
AC_PROG_GCC_TRADITIONAL
AC_OPENMP

CC_CHECK_FLAGS_APPEND([with_cflags], [CFLAGS], [\
	-pipe \
	-Wall \
	-Wextra \
	-Wno-inline \
	-Wundef \
	"-Wformat=2 -Wformat-security -Wformat-nonliteral" \
	-Wno-unused-parameter \
	-Wno-unused-result \
	-fno-strict-aliasing \
	-ffunction-sections \
	-fdata-sections \
	-fstack-protector-all \
	--param=ssp-buffer-size=4])
AC_SUBST([OUR_CFLAGS], $with_cflags)

AS_CASE([$CFLAGS], [*-O[[12345g\ ]]*],
	[CC_CHECK_FLAGS_APPEND([with_cppflags], [CPPFLAGS], [\
		-Wp,-D_FORTIFY_SOURCE=2])],
	[AC_MSG_RESULT([skipping -D_FORTIFY_SOURCE, optimization not enabled])])
AC_SUBST([OUR_CPPFLAGS], $with_cppflags)

CC_CHECK_FLAGS_APPEND([with_ldflags], [LDFLAGS], [\
	-Wl,--as-needed \
	-Wl,--no-undefined \
	-Wl,--gc-sections \
	-Wl,-z,relro \
	-Wl,-z,now])
AC_SUBST([OUR_LDFLAGS], $with_ldflags)

# Bison & Flex
AC_PROG_YACC
AM_PROG_LEX

# Python
AM_PATH_PYTHON([3.6])

AC_C_CONST
AC_CHECK_LIB([m], [round])

AC_CHECK_HEADERS([ \
	assert.h \
	ctypes.h \
	fcntl.h \
	math.h \
	regex.h \
	sched.h \
	stdarg.h \
	stdlib.h \
	string.h \
	syslog.h \
	sys/epoll.h \
	sys/personality.h \
	sys/stat.h \
	unistd.h
])

AC_CHECK_FUNCS([ \
	assert \
	epoll_ctl \
	epoll_create1 \
	epoll_wait \
	fnctl \
	personality \
	secure_getenv \
	strcmp \
	strdup \
	unshare
])

save_LIBS="$LIBS"

# libdl
LIBS=
AC_SEARCH_LIBS([dlsym], [dl], [], [AC_MSG_ERROR([*** Dynamic linking loader library not found])])
DL_LIBS="$LIBS"
AC_SUBST(DL_LIBS)

# libcap
AC_CHECK_HEADERS([sys/capability.h], [], [AC_MSG_ERROR([*** POSIX caps headers not found])])

LIBS=
AC_SEARCH_LIBS([cap_init], [cap], [], [AC_MSG_ERROR([*** POSIX caps library not found])])
CAP_LIBS="$LIBS"
AC_SUBST(CAP_LIBS)

# libsolv
AC_CHECK_HEADERS([solv/solvversion.h], [], [AC_MSG_ERROR([*** libsolv headers not found])])

LIBS=
AC_SEARCH_LIBS([solver_create], [solv], [], [AC_MSG_ERROR([*** libsolv library not found])])
SOLV_LIBS="$LIBS"
AC_SUBST(SOLV_LIBS)
LIBS="$save_LIBS"

PKG_CHECK_MODULES([ARCHIVE], [libarchive >= 3.3.3])
PKG_CHECK_MODULES([PYTHON_DEVEL], [python-${PYTHON_VERSION}])
PKG_CHECK_MODULES([LZMA], [liblzma])

AM_PATH_LIBGCRYPT([1.8.0], [], [AC_MSG_ERROR([*** libgcrypt not found])])
AM_PATH_GPGME([1.6.0], [], [AC_MSG_ERROR([*** GPGME not found])])

AC_ARG_WITH([systemdsystemunitdir],
	AS_HELP_STRING([--with-systemdsystemunitdir=DIR], [Directory for systemd service files]),
	[], [with_systemdsystemunitdir=$($PKG_CONFIG --variable=systemdsystemunitdir systemd)])
AC_SUBST([systemdsystemunitdir], [$with_systemdsystemunitdir])
AM_CONDITIONAL(HAVE_SYSTEMD, [test -n "$with_systemdsystemunitdir"])

AC_DEFINE_UNQUOTED([PAKFIRE_PRIVATE_DIR], ["/var/lib/${PACKAGE_NAME}"],
	[The path where Pakfire stores its private data])

AC_CONFIG_FILES([
	Makefile
	po/Makefile.in
	src/pakfire/__version__.py
])

AC_OUTPUT
AC_MSG_RESULT([
	$PACKAGE_NAME $VERSION

	Debug:                  ${enable_debug}

	CFLAGS:                 ${OUR_CFLAGS} ${CFLAGS}
	CPPFLAGS:               ${OUR_CPPFLAGS} ${CPPFLAGS}
	LDFLAGS:                ${OUR_LDFLAGS} ${LDFLAGS}
	PYTHON_CFLAGS:          ${PYTHON_DEVEL_CFLAGS}
	PYTHON_LIBS:            ${PYTHON_DEVEL_LIBS}
])
