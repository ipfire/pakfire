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
#include <string.h>
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

	// File descriptors
	int stdout[2];
	int stderr[2];
};

static int pakfire_execute_fork(void* data) {
	struct pakfire_execute* env = (struct pakfire_execute*)data;

	Pakfire pakfire = env->pakfire;

	const char* root = pakfire_get_path(pakfire);
	const char* arch = pakfire_get_arch(pakfire);

	DEBUG(pakfire, "Execution environment has been forked as PID %d\n", getpid());
	DEBUG(pakfire, "	root	: %s\n", root);

	for (unsigned int i = 0; env->argv[i]; i++)
		DEBUG(pakfire, "	argv[%u]	: %s\n", i, env->argv[i]);

	for (unsigned int i = 0; env->envp[i]; i++)
		DEBUG(pakfire, "	env	: %s\n", env->envp[i]);

	// Change root (unless root is /)
	if (strcmp(root, "/") != 0) {
		int r = chroot(root);
		if (r) {
			ERROR(pakfire, "chroot() to %s failed: %s\n", root, strerror(errno));

			return 1;
		}
	}

	// Set personality
	unsigned long persona = pakfire_arch_personality(arch);
	if (persona) {
		int r = personality(persona);
		if (r < 0) {
			ERROR(pakfire, "Could not set personality (%x)\n", (unsigned int)persona);

			return 1;
		}
	}

	// Connect standard output and error
	if (env->stdout[1] && env->stderr[1]) {
		if (dup2(env->stdout[1], STDOUT_FILENO) < 0) {
			ERROR(pakfire, "Could not connect fd %d to stdout: %s\n",
				env->stdout[1], strerror(errno));

			return 1;
		}

		if (dup2(env->stderr[1], STDERR_FILENO) < 0) {
			ERROR(pakfire, "Could not connect fd %d to stderr: %s\n",
				env->stderr[1], strerror(errno));

			return 1;
		}

		// Close the reading sides of the pipe
		close(env->stdout[0]);
		close(env->stderr[0]);

		// Close standard input
		close(STDIN_FILENO);
	}

	// exec() command
	int r = execve(env->argv[0], (char**)env->argv, env->envp);
	if (r < 0) {
		ERROR(pakfire, "Could not execve(): %s\n", strerror(errno));
	}

	// We should not get here
	return 1;
}

PAKFIRE_EXPORT int pakfire_execute(Pakfire pakfire, const char* argv[], char* envp[], int flags) {
	struct pakfire_execute env = {
		.pakfire = pakfire,
		.argv = argv,
		.envp = envp,
	};

	// Allocate stack
	char stack[4096];

	// argv is invalid
	if (!argv || !argv[0])
		return -EINVAL;

	if (!env.envp)
		env.envp = envp_empty;

	// Configure the new namespace
	int cflags = CLONE_VFORK | SIGCHLD | CLONE_NEWIPC | CLONE_NEWNS | CLONE_NEWUTS;

	// Enable network?
	if (!(flags & PAKFIRE_EXECUTE_ENABLE_NETWORK))
		cflags |= CLONE_NEWNET;

	// Make some file descriptors for stdout & stderr
	if (flags & PAKFIRE_EXECUTE_LOG_OUTPUT) {
		if (pipe(env.stdout) < 0) {
			ERROR(pakfire, "Could not create file descriptors for stdout: %s\n",
				strerror(errno));

			return -errno;
		}

		if (pipe(env.stderr) < 0) {
			ERROR(pakfire, "Could not create file descriptors for stderr: %s\n",
				strerror(errno));

			return -errno;
		}
	}

	// Fork this process
	pid_t pid = clone(pakfire_execute_fork, stack + sizeof(stack), cflags, &env);
	if (pid < 0) {
		ERROR(pakfire, "Could not fork: %s\n", strerror(errno));

		return -errno;
	}

	// Close any unused file descriptors
	if (env.stdout[1])
		close(env.stdout[1]);
	if (env.stderr[1])
		close(env.stderr[1]);

	DEBUG(pakfire, "Waiting for PID %d to finish its work\n", pid);

	int status;
	waitpid(pid, &status, 0);

	// Set some useful error code
	int r = -ESRCH;

	if (WIFEXITED(status)) {
		r = WEXITSTATUS(status);

		DEBUG(pakfire, "Child process exited with code: %d\n", r);
	} else {
		ERROR(pakfire, "Could not determine the exit status of process %d\n", pid);
	}

	// Close any file descriptors
	if (env.stdout[0])
		close(env.stdout[0]);
	if (env.stderr[0])
		close(env.stderr[0]);

	return r;
}

PAKFIRE_EXPORT int pakfire_execute_command(Pakfire pakfire, const char* command, char* envp[], int flags) {
	const char* argv[2] = {
		command, NULL,
	};

	return pakfire_execute(pakfire, argv, envp, flags);
}
