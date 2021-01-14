/*#############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2019 Pakfire development team                                 #
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

#include <errno.h>
#include <sched.h>
#include <stdlib.h>
#include <sys/personality.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <pakfire/arch.h>
#include <pakfire/execute.h>
#include <pakfire/logging.h>
#include <pakfire/private.h>
#include <pakfire/types.h>

static char* envp_empty[1] = { NULL };

struct pakfire_execute {
	Pakfire pakfire;
	const char** argv;
	char** envp;
};

static int pakfire_execute_fork(struct pakfire_execute* env) {
	Pakfire pakfire = env->pakfire;
	int r;

	pid_t pid = getpid();

	const char* root = pakfire_get_path(pakfire);

	DEBUG(pakfire, "Execution environment has been forked as PID %d\n", pid);
	DEBUG(pakfire, "	root	: %s\n", root);

	for (unsigned int i = 0; env->argv[i]; i++)
		DEBUG(pakfire, "	argv[%u]	: %s\n", i, env->argv[i]);

	for (unsigned int i = 0; env->envp[i]; i++)
		DEBUG(pakfire, "	env	: %s\n", env->envp[i]);

	// Move /
	r = chroot(root);
	if (r) {
		ERROR(pakfire, "chroot() to %s failed: %s\n", root, strerror(errno));
		return errno;
	}

	// Get architecture
	const char* arch = pakfire_get_arch(pakfire);

	// Set personality
	unsigned long persona = pakfire_arch_personality(arch);
	r = personality(persona);
	if (r < 0) {
		ERROR(pakfire, "Could not set personality (%x)\n", (unsigned int)persona);

		return errno;
	}

	// exec() command
	r = execve(env->argv[0], (char**)env->argv, env->envp);

	// We should not get here
	return errno;
}

PAKFIRE_EXPORT int pakfire_execute(Pakfire pakfire, const char* argv[], char* envp[], int flags) {
	struct pakfire_execute env = {
		.pakfire = pakfire,
		.argv = argv,
		.envp = envp,
	};

	// argv is invalid
	if (!argv || !argv[0])
		return -EINVAL;

	if (!env.envp)
		env.envp = envp_empty;

	// Fork this process
	pid_t pid = fork();

	if (pid < 0) {
		ERROR(pakfire, "Could not fork: %s\n", strerror(errno));
		return errno;

	// Child process
	} else if (pid == 0) {
		int r = pakfire_execute_fork(&env);

		ERROR(pakfire, "Forked process returned unexpectedly: %s\n",
			strerror(r));

		// Exit immediately
		exit(r);

	// Parent process
	} else {
		DEBUG(pakfire, "Waiting for PID %d to finish its work\n", pid);

		int status;
		waitpid(pid, &status, 0);

		if (WIFEXITED(status)) {
			int r = WEXITSTATUS(status);

			DEBUG(pakfire, "Child process has exited with code: %d\n", r);
			return r;
		}

		ERROR(pakfire, "Could not determine the exit status of process %d\n", pid);
		return -1;
	}

	return 0;
}

PAKFIRE_EXPORT int pakfire_execute_command(Pakfire pakfire, const char* command, char* envp[], int flags) {
	const char* argv[2] = {
		command, NULL,
	};

	return pakfire_execute(pakfire, argv, envp, flags);
}
