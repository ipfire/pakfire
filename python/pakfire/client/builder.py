#!/usr/bin/python

import hashlib
import multiprocessing
import os
import sys
import tempfile
import time

import pakfire.api
import pakfire.builder
import pakfire.config
import pakfire.downloader
import pakfire.system
import pakfire.util
from pakfire.system import system

import base

from pakfire.constants import *

import logging
log = logging.getLogger("pakfire.client")

def fork_builder(*args, **kwargs):
	"""
		Wrapper that runs ClientBuilder in a new process and catches
		any exception to report it to the main process.
	"""
	try:
		# Create new instance of the builder.
		cb = ClientBuilder(*args, **kwargs)

		# Run the build:
		cb.build()

	except Exception, e:
		# XXX catch the exception and log it.
		print e

		# End the process with an exit code.
		sys.exit(1)


class PakfireDaemon(object):
		"""
			The PakfireDaemon class that creates a a new process per build
			job and also handles the keepalive/abort stuff.
		"""
		def __init__(self, server, hostname, secret):
			self.client = base.PakfireBuilderClient(server, hostname, secret)
			self.conn   = self.client.conn

			# Save login data (to create child processes).
			self.server = server
			self.hostname = hostname
			self.__secret = secret

			# A list with all running processes.
			self.processes = []
			self.pid2jobid = {}

			# Save when last keepalive was sent.
			self._last_keepalive = 0

		def run(self, heartbeat=1, max_processes=None):
			# By default do not start more than two processes per CPU core.
			if max_processes is None:
				max_processes = system.cpu_count * 2
			log.debug("Maximum number of simultaneous processes is: %s" % max_processes)

			# Indicates when to try to request a new job or aborted builds.
			last_job_request = 0
			last_abort_request = 0

			# Main loop.
			while True:
				# Send the keepalive regularly.
				self.send_keepalive()

				# Remove all finished builds.
				# "removed" indicates, if a process has actually finished.
				removed = self.remove_finished_builders()

				# If a build slot was freed, search immediately for a new job.
				if removed:
					last_job_request = 0

				# Kill aborted jobs.
				if time.time() - last_abort_request >= 60:
					aborted = self.kill_aborted_jobs()

					# If a build slot was freed, search immediately for a new job.
					if aborted:
						last_job_request = 0

					last_abort_request = time.time()

				# Check if the maximum number of processes was reached.
				# Actually the hub does manage this but this is an emergency
				# condition if anything goes wrong.
				if self.num_processes >= max_processes:
					log.debug("Reached maximum number of allowed processes (%s)." % max_processes)

					time.sleep(heartbeat)
					continue

				# Get new job.
				if time.time() - last_job_request >= 60 and not self.has_overload():
					# If the last job request is older than a minute and we don't
					# have too much load, we go and check if there is something
					# to do for us.
					job = self.get_job()

					# If we got a job, we start a child process to work on it.
					if job:
						log.debug("Got a new job.")
						self.fork_builder(job)
					else:
						log.debug("No new job.")

					# Update the time when we requested a job.
					last_job_request = time.time()

				# Wait a moment before starting over.
				time.sleep(heartbeat)

		def shutdown(self):
			"""
				Shut down the daemon.
				This means to kill all child processes.

				The method blocks until all processes are shut down.
			"""
			for process in self.processes:
				log.info("Sending %s to terminate..." % process)

				process.terminate()
			else:
				log.info("No processes to kill. Shutting down immediately.")

			while self.processes:
				log.debug("%s process(es) is/are still running..." % len(self.processes))

				for process in self.processes[:]:
					if not process.is_alive():
						# The process has terminated.
						log.info("Process %s terminated with exit code: %s" % \
							(process, process.exitcode))

						self.processes.remove(process)

		@property
		def num_processes(self):
			# Return the number of processes.
			return len(self.processes)

		def get_job(self):
			"""
				Get a build job from the hub.
			"""
			log.info("Requesting a new job from the server...")

			# Get some information about this system.
			s = pakfire.system.System()

			# Fetch a build job from the hub.
			return self.client.conn.build_get_job(s.supported_arches)

		def has_overload(self):
			"""
				Checks, if the load average is not too high.

				On this is to be decided if a new job is taken.
			"""
			try:
				load1, load5, load15 = os.getloadavg()
			except OSError:
				# Could not determine the current loadavg. In that case we
				# assume that we don't have overload.
				return False

			# If there are more than 2 processes in the process queue per CPU
			# core we will assume that the system has heavy load and to not request
			# a new job.
			return load5 >= system.cpu_count * 2

		def send_keepalive(self):
			"""
				When triggered, this method sends a keepalive to the hub.
			"""
			# Do not send a keepalive more often than twice a minute.
			if time.time() - self._last_keepalive < 30:
				return

			self.client.send_keepalive(overload=self.has_overload())
			self._last_keepalive = time.time()

		def remove_finished_builders(self):
			# Return if any processes have been removed.
			ret = False

			# Search for any finished processes.
			for process in self.processes[:]:
				# If the process is not alive anymore...
				if not process.is_alive():
					ret = True

					# ... check the exit code and log a message on errors.
					if process.exitcode == 0:
						log.debug("Process %s exited normally." % process)

					elif process.exitcode > 0:
						log.error("Process did not exit normally: %s code: %s" \
							% (process, process.exitcode))

					elif process.exitcode < 0:
						log.error("Process killed by signal: %s: code: %s" \
							% (process, process.exitcode))

						# If a program has crashed, we send that to the hub.
						job_id = self.pid2jobid.get(process.pid, None)
						if job_id:
							self.conn.build_job_crashed(job_id, process.exitcode)

					# Finally, remove the process from the process list.
					self.processes.remove(process)

			return ret

		def kill_aborted_jobs(self):
			log.debug("Requesting aborted jobs...")

			# Get a list of running job ids:
			running_jobs = self.pid2jobid.values()

			# If there are no running jobs, there is nothing to do.
			if not running_jobs:
				return False

			# Ask the hub for any build jobs to abort.
			aborted_jobs = self.conn.build_jobs_aborted(running_jobs)

			# If no build jobs were aborted, there is nothing to do.
			if not aborted_jobs:
				return False

			for process in self.processes[:]:
				job_id = self.pid2jobid.get(process.pid, None)
				if job_id and job_id in aborted_jobs:

					# Kill the process.
					log.info("Killing process %s which was aborted by the user." \
						% process.pid)
					process.terminate()

					# Remove the process from the process list to avoid
					# that is will be cleaned up in the normal way.
					self.processes.remove(process)

			return True

		def fork_builder(self, job):
			"""
				For a new child process to create a new independent builder.
			"""
			# Create the Process object.
			process = multiprocessing.Process(target=fork_builder,
				args=(self.server, self.hostname, self.__secret, job))
			# The process is running in daemon mode so it will try to kill
			# all child processes when exiting.
			process.daemon = True

			# Start the process.
			process.start()
			log.info("Started new process %s with PID %s." % (process, process.pid))

			# Save the PID and the build id to track down
			# crashed builds.
			self.pid2jobid[process.pid] = job.get("id", None)

			# Append it to the process list.
			self.processes.append(process)


class ClientBuilder(object):
	def __init__(self, server, hostname, secret, job):
		self.client = base.PakfireBuilderClient(server, hostname, secret)
		self.conn   = self.client.conn

		# Store the information sent by the server here.
		self.build_job = job

	def update_state(self, state, message=None):
		self.conn.build_job_update_state(self.build_id, state, message)

	def upload_file(self, filename, type):
		assert os.path.exists(filename)
		assert type in ("package", "log")

		# First upload the file data and save the upload_id.
		upload_id = self.client._upload_file(filename)

		# Add the file to the build.
		return self.conn.build_job_add_file(self.build_id, upload_id, type)

	def upload_buildroot(self, installed_packages):
		pkgs = []

		for pkg in installed_packages:
			pkgs.append((pkg.friendly_name, pkg.uuid))

		return self.conn.build_upload_buildroot(self.build_id, pkgs)

	@property
	def build_id(self):
		if self.build_job:
			return self.build_job.get("id", None)

	@property
	def build_arch(self):
		if self.build_job:
			return self.build_job.get("arch", None)

	@property
	def build_source_url(self):
		if self.build_job:
			return self.build_job.get("source_url", None)

	@property
	def build_source_filename(self):
		if self.build_source_url:
			return os.path.basename(self.build_source_url)

	@property
	def build_source_hash512(self):
		if self.build_job:
			return self.build_job.get("source_hash512", None)

	@property
	def build_type(self):
		if self.build_job:
			return self.build_job.get("type", None)

	def build(self):
		# Cannot go on if I got no build job.
		if not self.build_job:
			logging.info("No job to work on...")
			return

		# Call the function that processes the build and try to catch general
		# exceptions and report them to the server.
		# If everything goes okay, we tell this the server, too.
		try:
			# Create a temporary file and a directory for the resulting files.
			tmpdir  = tempfile.mkdtemp()
			tmpfile = os.path.join(tmpdir, self.build_source_filename)
			logfile = os.path.join(tmpdir, "build.log")

			# Get a package grabber and add mirror download capabilities to it.
			grabber = pakfire.downloader.PackageDownloader(pakfire.config.Config())

			try:
				## Download the source.
				grabber.urlgrab(self.build_source_url, filename=tmpfile)

				# Check if the download checksum matches (if provided).
				if self.build_source_hash512:
					h = hashlib.sha512()
					f = open(tmpfile, "rb")
					while True:
						buf = f.read(BUFFER_SIZE)
						if not buf:
							break

						h.update(buf)
					f.close()

					if not self.build_source_hash512 == h.hexdigest():
						raise DownloadError, "Hash check did not succeed."

				# Create dist with arguments that are passed to the pakfire
				# builder.
				kwargs = {
					# Of course this is a release build.
					# i.e. don't use local packages.
					"builder_mode"  : "release",

					# Set the build_id we got from the build service.
					"build_id"      : self.build_id,

					# Files and directories (should be self explaining).
					"logfile"       : logfile,

					# Distro configuration.
					"distro_config" : {
						"arch" : self.build_arch,
					},
				}

				# Create a new instance of the builder.
				build = pakfire.builder.BuildEnviron(tmpfile, **kwargs)

				try:
					# Create the build environment.
					build.start()

					# Update the build status on the server.
					self.upload_buildroot(build.installed_packages)
					self.update_state("running")

					# Run the build (with install test).
					build.build(install_test=True)

					# Copy the created packages to the tempdir.
					build.copy_result(tmpdir)

				finally:
					# Cleanup the build environment.
					build.stop()

				# Jippie, build is finished, we are going to upload the files.
				self.update_state("uploading")

				# Walk through the result directory and upload all (binary) files.
				# Skip that for test builds.
				if not self.build_type == "test":
					for dir, subdirs, files in os.walk(tmpdir):
						for file in files:
							file = os.path.join(dir, file)
							if file in (logfile, tmpfile,):
								continue

							self.upload_file(file, "package")

			except DependencyError, e:
				message = "%s: %s" % (e.__class__.__name__, e)
				self.update_state("dependency_error", message)
				raise

			except DownloadError, e:
				message = "%s: %s" % (e.__class__.__name__, e)
				self.update_state("download_error", message)
				raise

			finally:
				# Upload the logfile in any case and if it exists.
				if os.path.exists(logfile):
					self.upload_file(logfile, "log")

				# Cleanup the files we created.
				pakfire.util.rm(tmpdir)

		except DependencyError:
			# This has already been reported.
			raise

		except (DownloadError,):
			# Do not take any further action for these exceptions.
			pass

		except Exception, e:
			# Format the exception and send it to the server.
			message = "%s: %s" % (e.__class__.__name__, e)

			self.update_state("failed", message)
			raise

		else:
			self.update_state("finished")
