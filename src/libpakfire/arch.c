/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2021 Pakfire development team                                 #
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
#############################################################################*/

#include <ctype.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

#include <pakfire/arch.h>
#include <pakfire/constants.h>
#include <pakfire/private.h>
#include <pakfire/util.h>

struct pakfire_arch {
	const char* name;
	const char* platform;
	const char* compatible[5];
};

static const struct pakfire_arch PAKFIRE_ARCHES[] = {
	// x86
	{
		.name = "x86_64",
		.platform = "x86",
		.compatible = { "i686", NULL },
	},
	{
		.name = "i686",
		.platform = "x86",
	},

	// ARM
	{
		.name = "aarch64",
		.platform = "arm",
	},
	{
		.name = "armv7hl",
		.platform = "arm",
		.compatible = { "armv7l", "armv6l", "armv5tejl", "armv5tel", NULL },
	},
	{
		.name = "armv7l",
		.platform = "arm",
		.compatible = { "armv6l", "armv5tejl", "armv5tel", NULL },
	},
	{
		.name = "armv6l",
		.platform = "arm",
		.compatible = { "armv5tejl", "armv5tel", NULL },
	},
	{
		.name = "armv5tejl",
		.platform = "arm",
		.compatible = { "armv5tel", NULL },
	},
	{
		.name = "armv5tel",
		.platform = "arm",
	},
};

static const struct pakfire_arch* pakfire_arch_find(const char* name) {
	const size_t length = sizeof(PAKFIRE_ARCHES) / sizeof(*PAKFIRE_ARCHES);

	for (unsigned int i = 0; i < length; i++) {
		const struct pakfire_arch* arch = &PAKFIRE_ARCHES[i];

		if (strcmp(arch->name, name) == 0)
			return arch;
	}

	return NULL;
}

PAKFIRE_EXPORT int pakfire_arch_supported(const char* name) {
	const struct pakfire_arch* arch = pakfire_arch_find(name);

	if (arch)
		return 1;

	return 0;
}

PAKFIRE_EXPORT const char* pakfire_arch_platform(const char* name) {
	const struct pakfire_arch* arch = pakfire_arch_find(name);

	if (arch && arch->platform)
		return arch->platform;

	return NULL;
}

PAKFIRE_EXPORT char* pakfire_arch_machine(const char* arch, const char* vendor) {
	if (!vendor)
		vendor = "unknown";

	// Format string
	char buffer[STRING_SIZE];
	snprintf(buffer, STRING_SIZE - 1, "%s-%s-linux-gnu", arch, vendor);

	// Make everything lowercase
	for (unsigned int i = 0; i < strlen(buffer); i++)
		buffer[i] = tolower(buffer[i]);

	return pakfire_strdup(buffer);
}

static const char* __pakfire_arch_native = NULL;

PAKFIRE_EXPORT const char* pakfire_arch_native() {
	struct utsname buf;

	if (!__pakfire_arch_native) {
		if (uname(&buf) < 0)
			return NULL;

		__pakfire_arch_native = pakfire_strdup(buf.machine);
	}

	return __pakfire_arch_native;
}

PAKFIRE_EXPORT int pakfire_arch_is_compatible(const char* name, const char* compatible_arch) {
	// Every architecture is compatible with itself
	if (strcmp(name, compatible_arch) == 0)
		return 1;

	const struct pakfire_arch* arch = pakfire_arch_find(name);
	if (!arch)
		return 0;

	for (unsigned int i = 0; arch->compatible[i]; i++) {
		if (strcmp(arch->compatible[i], compatible_arch) == 0)
			return 1;
	}

	return 0;
}

PAKFIRE_EXPORT int pakfire_arch_supported_by_host(const char* name) {
	const char* native_arch = pakfire_arch_native();

	// Check if those two architectures are compatible
	return pakfire_arch_is_compatible(native_arch, name);
}
