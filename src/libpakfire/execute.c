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
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#include <pakfire/execute.h>
#include <pakfire/logging.h>
#include <pakfire/private.h>
#include <pakfire/types.h>

#define STACK_SIZE 1024

struct pakfire_execute_env {
    Pakfire pakfire;
    const char* root;
    const char* command;
    const char** argv;
    const char** envp;
};

static int pakfire_execute_fork(Pakfire pakfire, struct pakfire_execute_env* env) {
    pid_t pid = getpid();

    DEBUG(env->pakfire, "Execution environment has been forked as PID %d\n", pid);
    DEBUG(env->pakfire, " command = %s, root = %s\n", env->command, env->root);

    // Move /
    int r = chroot(env->root);
    if (r) {
        ERROR(env->pakfire, "chroot() to %s failed: %s\n",
            env->root, strerror(errno));
        return errno;
    }

    // exec() command
    r = execve(env->command, (char**)env->argv, (char**)env->envp);

    // We should not get here
    return errno;
}

PAKFIRE_EXPORT int pakfire_execute(Pakfire pakfire, const char* command, const char** argv,
		const char** envp, int flags) {
    struct pakfire_execute_env env;

    // Setup environment
    env.pakfire = pakfire;
    env.root = pakfire_get_path(pakfire);

    env.command = command;
    env.argv = argv;
    env.envp = envp;

    // Fork this process
    pid_t pid = fork();

    if (pid < 0) {
        ERROR(pakfire, "Could not fork: %s\n", strerror(errno));
        return errno;

    // Child process
    } else if (pid == 0) {
        int r = pakfire_execute_fork(pakfire, &env);

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
