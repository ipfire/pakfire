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
#include <fcntl.h>
#include <sched.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/personality.h>
#include <sys/types.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

#include <pakfire/arch.h>
#include <pakfire/execute.h>
#include <pakfire/logging.h>
#include <pakfire/private.h>
#include <pakfire/types.h>

#define EPOLL_MAX_EVENTS 2

static char* envp_empty[1] = { NULL };

struct pakfire_execute {
	Pakfire pakfire;
	const char** argv;
	char** envp;

	// File descriptors
	int stdout[2];
	int stderr[2];
};

struct pakfire_execute_buffer {
	char* data;
	size_t size;
	size_t used;
};

static int pakfire_execute_buffer_realloc(Pakfire pakfire, struct pakfire_execute_buffer* buffer, size_t size) {
	// We cannot decrease the buffer size
	if (size <= buffer->size)
		return -EINVAL;

	// Allocate the new buffer
	buffer->data = realloc(buffer->data, size);
	if (!buffer->data)
		return -errno;

	buffer->size = size;

	DEBUG(pakfire, "Buffer %p is now %zu byte(s) long\n", buffer, buffer->size);

	return 0;
}

static int pakfire_execute_buffer_init(Pakfire pakfire, struct pakfire_execute_buffer* buffer) {
	// Initialize all values with nothing
	buffer->data = NULL;
	buffer->size = buffer->used = 0;

	// Allocate one page
	return pakfire_execute_buffer_realloc(pakfire, buffer, PAGE_SIZE);
}

static void pakfire_execute_buffer_free(struct pakfire_execute_buffer* buffer) {
	if (buffer->data)
		free(buffer->data);

	buffer->size = buffer->used = 0;
}

static int pakfire_execute_buffer_is_full(const struct pakfire_execute_buffer* buffer) {
	return (buffer->size == buffer->used);
}

/*
	This function reads as much data as it can from the file descriptor.
	If it finds a whole line in it, it will send it to the logger and repeat the process.
	If not newline character is found, it will try to read more data until it finds one.
*/
static int pakfire_execute_logger_proxy(Pakfire pakfire,
		int(*log_func)(Pakfire pakfire, const char* data), int fd, struct pakfire_execute_buffer* buffer) {
	// Fill up buffer from fd
	while (buffer->used < buffer->size) {
		ssize_t bytes_read = read(fd, buffer->data + buffer->used,
				buffer->size - buffer->used);

		// Handle errors
		if (bytes_read < 0) {
			// Try again?
			if (errno == EAGAIN)
				continue;

			ERROR(pakfire, "Could not read from fd %d: %s\n", fd, strerror(errno));
			return -1;

		} else if (bytes_read == 0)
			break;

		// Update buffer size
		buffer->used += bytes_read;
	}

	// See if we have any lines that we can write
	while (buffer->used) {
		// Search for the end of the first line
		char* eol = memchr(buffer->data, '\n', buffer->used);

		// No newline found
		if (!eol) {
			// If the buffer is full, we double its size and try to read more
			if (pakfire_execute_buffer_is_full(buffer)) {
				int r = pakfire_execute_buffer_realloc(pakfire, buffer, buffer->size * 2);
				if (r)
					return -1;

				return pakfire_execute_logger_proxy(pakfire, log_func, fd, buffer);
			}

			// Otherwise we might have only read parts of the output
			return 0;
		}

		// Find the length of the string
		size_t length = eol - buffer->data + 1;

		DEBUG(pakfire, "Found a line of %zu byte(s) length\n", length);

		// Allocate a new buffer that is large enough to hold the line
		char* line = alloca(length + 1);

		// Copy the line into the buffer
		memcpy(line, buffer->data, length);

		// Terminate the string
		line[length] = '\0';

		// Log the line
		int r = log_func(pakfire, line);
		if (r)
			return r;

		// Remove line from buffer
		memmove(buffer->data, buffer->data + length, buffer->used - length);
		buffer->used -= length;
	}

	return 0;
}

static int pakfire_execute_logger(Pakfire pakfire, struct pakfire_execute_logger* logger,
		pid_t pid, int stdout, int stderr, int* status) {
	int epollfd = -1;
	struct epoll_event ev;
	struct epoll_event events[EPOLL_MAX_EVENTS];
	int r = 0;

	int fds[2] = {
		stdout, stderr,
	};

	// Allocate buffers
	struct buffers {
		struct pakfire_execute_buffer stdout;
		struct pakfire_execute_buffer stderr;
	} buffers;

	r = pakfire_execute_buffer_init(pakfire, &buffers.stdout);
	if (r) {
		ERROR(pakfire, "Could not initialize buffer for stdout: %s\n", strerror(errno));
		goto OUT;
	}

	r = pakfire_execute_buffer_init(pakfire, &buffers.stderr);
	if (r) {
		ERROR(pakfire, "Could not initialize buffer for stderr: %s\n", strerror(errno));
		goto OUT;
	}

	// Setup epoll
	epollfd = epoll_create1(0);
	if (epollfd < 0) {
		ERROR(pakfire, "Could not initialize epoll(): %s\n", strerror(errno));
		r = -errno;
		goto OUT;
	}

	ev.events = EPOLLIN;

	// Turn file descriptors into non-blocking mode and add them to epoll()
	for (unsigned int i = 0; i < 2; i++) {
		int fd = fds[i];

		// Read flags
		int flags = fcntl(fd, F_GETFL, 0);

		// Set modified flags
		if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) {
			ERROR(pakfire, "Could not set file descriptor %d into non-blocking mode: %s\n",
				fd, strerror(errno));
			r = -errno;
			goto OUT;
		}

		ev.data.fd = fd;

		if (epoll_ctl(epollfd, EPOLL_CTL_ADD, fd, &ev) < 0) {
			ERROR(pakfire, "Could not add file descriptor %d to epoll(): %s\n",
				fd, strerror(errno));
			r = -errno;
			goto OUT;
		}
	}

	// Loop for as long as the process is alive
	while (waitpid(pid, status, WNOHANG) == 0) {
		int fds = epoll_wait(epollfd, events, EPOLL_MAX_EVENTS, -1);
		if (fds < 1) {
			ERROR(pakfire, "epoll_wait() failed: %s\n", strerror(errno));
			r = -errno;

			goto OUT;
		}

		struct pakfire_execute_buffer* buffer;
		int (*log_func)(Pakfire pakfire, const char* data);

		for (int i = 0; i < fds; i++) {
			int fd = events[i].data.fd;

			if (fd == stdout) {
				buffer = &buffers.stdout;
				log_func = logger->log_stdout;

			} else if (fd == stderr) {
				buffer = &buffers.stderr;
				log_func = logger->log_stderr;

			} else {
				DEBUG(pakfire, "Received invalid file descriptor %d\n", fd);
				continue;
			}

			// Send everything to the logger
			r = pakfire_execute_logger_proxy(pakfire, log_func, fd, buffer);
			if (r)
				goto OUT;
		}
	}

OUT:
	if (epollfd > 0)
		close(epollfd);

	// Free buffers
	pakfire_execute_buffer_free(&buffers.stdout);
	pakfire_execute_buffer_free(&buffers.stderr);

	return r;
}

static int default_log_stdout(Pakfire pakfire, const char* line) {
	INFO(pakfire, "%s", line);

	return 0;
}

static int default_log_stderr(Pakfire pakfire, const char* line) {
	ERROR(pakfire, "%s", line);

	return 0;
}

static struct pakfire_execute_logger default_logger = {
	.log_stdout = default_log_stdout,
	.log_stderr = default_log_stderr,
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

PAKFIRE_EXPORT int pakfire_execute(Pakfire pakfire, const char* argv[], char* envp[],
		int flags, struct pakfire_execute_logger* logger) {
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

	if (!logger)
		logger = &default_logger;

	// Configure the new namespace
	int cflags = CLONE_VFORK | SIGCHLD | CLONE_NEWIPC | CLONE_NEWNS | CLONE_NEWUTS;

	// Enable network?
	if (!(flags & PAKFIRE_EXECUTE_ENABLE_NETWORK))
		cflags |= CLONE_NEWNET;

	// Make some file descriptors for stdout & stderr
	if (!(flags & PAKFIRE_EXECUTE_INTERACTIVE)) {
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

	// Set some useful error code
	int r = -ESRCH;
	int status;

	DEBUG(pakfire, "Waiting for PID %d to finish its work\n", pid);

	if (!(flags & PAKFIRE_EXECUTE_INTERACTIVE)) {
		// Close any unused file descriptors
		if (env.stdout[1])
			close(env.stdout[1]);
		if (env.stderr[1])
			close(env.stderr[1]);

		if (pakfire_execute_logger(pakfire, logger, pid, env.stdout[0], env.stderr[0], &status)) {
			ERROR(pakfire, "Log reading aborted: %s\n", strerror(errno));
		}
	}

	if (!status)
		waitpid(pid, &status, 0);

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

PAKFIRE_EXPORT int pakfire_execute_command(Pakfire pakfire, const char* command, char* envp[],
		int flags, struct pakfire_execute_logger* logger) {
	const char* argv[2] = {
		command, NULL,
	};

	return pakfire_execute(pakfire, argv, envp, flags, logger);
}
