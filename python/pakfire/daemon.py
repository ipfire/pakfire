#!/usr/bin/python

import hashlib
import json
import multiprocessing
import os
import signal
import sys
import tempfile
import time

import pakfire.base
import pakfire.builder
import pakfire.config
import pakfire.downloader
import pakfire.system
import pakfire.util
from pakfire.system import system

import base
import transport

from pakfire.constants import *
from pakfire.i18n import _

import logging
log = logging.getLogger("pakfire.daemon")

class BuildJob(dict):
	"""
		Wrapper class for build jobs, that are received from the hub.

		This makes accessing attributes more easy.
	"""
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError, key


class PakfireDaemon(object):
	def __init__(self, config):
		self.config = config

		# Indicates if this daemon is in running mode.
		self.__running = True

		# Create daemon that sends keep-alive messages.
		self.keepalive = PakfireDaemonKeepalive(self.config)

		# List of worker processes.
		self.__workers = [self.keepalive]

		### Configuration
		# Number of workers in waiting state.
		self.max_waiting = 1

		# Number of running workers.
		self.max_running = system.cpu_count * 2

	def run(self, heartbeat=30):
		"""
			Main loop.
		"""
		# Register signal handlers.
		self.register_signal_handlers()

		# Start keepalive process.
		self.keepalive.start()

		# Run main loop.
		while self.__running:
			time_started = time.time()

			# Spawn a sufficient number of worker processes.
			self.spawn_workers_if_needed()

			# Get runtime of this loop iteration.
			time_elapsed = time.time() - time_started

			# Wait if the heartbeat time has not been reached, yet.
			if time_elapsed < heartbeat:
				time.sleep(heartbeat - time_elapsed)

		# Main loop has ended, but we wait until all workers have finished.
		self.terminate_all_workers()

	def shutdown(self):
		"""
			Terminates all workers and exists the daemon.
		"""
		if not self.__running:
			return

		log.info(_("Shutting down..."))
		self.__running = False

	def spawn_workers_if_needed(self, *args, **kwargs):
		"""
			Spawns more workers if needed.
		"""
		# Do not create any more processes when the daemon is shutting down.
		if not self.__running:
			return

		# Cleanup all other workers.
		self.cleanup_workers()

		# Do not create more workers if there are already enough workers
		# active.
		if len(self.workers) >= self.max_running:
			log.warning("More workers running than allowed")
			return

		# Do nothing, if there is are already enough workers waiting.
		wanted_waiting_workers = self.max_waiting - len(self.waiting_workers)
		if wanted_waiting_workers <= 0:
			return

		# Spawn a new worker.
		for i in range(wanted_waiting_workers):
			self.spawn_worker(*args, **kwargs)

	def spawn_worker(self, *args, **kwargs):
		"""
			Spawns a new worker process.
		"""
		worker = PakfireWorker(config=self.config, *args, **kwargs)
		worker.start()

		log.debug("Spawned new worker process: %s" % worker)
		self.__workers.append(worker)

	def terminate_worker(self, worker):
		"""
			Terminates the given worker.
		"""
		log.warning(_("Terminating worker process: %s") % worker)

		worker.terminate()

	def terminate_all_workers(self):
		"""
			Terminates all workers.
		"""
		for worker in self.workers:
			self.terminate_worker(worker)

			# Wait until the worker has finished.
			worker.join()

		# Terminate the keepalive process.
		self.terminate_worker(self.keepalive)
		self.keepalive.join()

	def remove_worker(self, worker):
		"""
			Removes a worker from the internal list of worker processes.
		"""
		assert not worker.is_alive(), "Remove alive worker?"

		log.debug("Removing worker: %s" % worker)
		try:
			self.__workers.remove(worker)
		except:
			pass

	def cleanup_workers(self):
		"""
			Remove workers that are not alive any more.
		"""
		for worker in self.workers:
			if worker.is_alive():
				continue

			self.remove_worker(worker)

	@property
	def workers(self):
		return [w for w in self.__workers if isinstance(w, PakfireWorker)]

	@property
	def running_workers(self):
		workers = []

		for worker in self.workers:
			if worker.waiting.is_set():
				continue

			workers.append(worker)

		return workers

	@property
	def waiting_workers(self):
		workers = []

		for worker in self.workers:
			if worker.waiting.is_set():
				workers.append(worker)

		return workers

	# Signal handling.

	def register_signal_handlers(self):
		signal.signal(signal.SIGCHLD, self.handle_SIGCHLD)
		signal.signal(signal.SIGINT,  self.handle_SIGTERM)
		signal.signal(signal.SIGTERM, self.handle_SIGTERM)

	def handle_SIGCHLD(self, signum, frame):
		"""
			Handle signal SIGCHLD.
		"""
		# Spawn new workers if necessary.
		self.spawn_workers_if_needed()

	def handle_SIGTERM(self, signum, frame):
		"""
			Handle signal SIGTERM.
		"""
		# Just shut down.
		self.shutdown()


class PakfireDaemonKeepalive(multiprocessing.Process):
	def __init__(self, config):
		multiprocessing.Process.__init__(self)

		# Save config.
		self.config = config

	def run(self, heartbeat=30):
		# Register signal handlers.
		self.register_signal_handlers()

		# Create connection to the hub.
		self.transport = transport.PakfireHubTransport(self.config)
		self.transport.fork()

		# Send our profile to the hub.
		self.send_builder_info()

		while True:
			time_started = time.time()

			# Send keepalive message.
			self.send_keepalive()

			# Get runtime of this loop iteration.
			time_elapsed = time.time() - time_started

			# Wait if the heartbeat time has not been reached, yet.
			if time_elapsed < heartbeat:
				time.sleep(heartbeat - time_elapsed)

	def shutdown(self):
		"""
			Ends this process immediately.
		"""
		sys.exit(1)

	# Signal handling.

	def register_signal_handlers(self):
		signal.signal(signal.SIGCHLD, self.handle_SIGCHLD)
		signal.signal(signal.SIGINT,  self.handle_SIGTERM)
		signal.signal(signal.SIGTERM, self.handle_SIGTERM)

	def handle_SIGCHLD(self, signum, frame):
		"""
			Handle signal SIGCHLD.
		"""
		# Must be here so that SIGCHLD won't be propagated to
		# PakfireDaemon.
		pass

	def handle_SIGTERM(self, signum, frame):
		"""
			Handle signal SIGTERM.
		"""
		# Just shut down.
		self.shutdown()

	# Talking to the hub.

	def send_builder_info(self):
		log.info(_("Sending builder information to hub..."))

		data = {
			# CPU info
			"cpu_model"       : system.cpu_model,
			"cpu_count"       : system.cpu_count,
			"cpu_arch"        : system.native_arch,
			"cpu_bogomips"    : system.cpu_bogomips,

			# Memory + swap
			"mem_total"       : system.memory,
			"swap_total"      : system.swap_total,

			# Pakfire + OS
			"pakfire_version" : PAKFIRE_VERSION,
			"host_key"        : self.config.get("signatures", "host_key", None),
			"os_name"         : system.distro.pretty_name,

			# Supported arches
			"supported_arches" : ",".join(system.supported_arches),
		}
		self.transport.post("/builders/info", data=data)

	def send_keepalive(self):
		log.debug("Sending keepalive message to hub...")

		data = {
			# Load average.
			"loadavg1"   : system.loadavg1,
			"loadavg5"   : system.loadavg5,
			"loadavg15"  : system.loadavg15,

			# Memory
			"mem_total"  : system.memory_total,
			"mem_free"   : system.memory_free,

			# Swap
			"swap_total" : system.swap_total,
			"swap_free"  : system.swap_free,

			# Disk space
			"space_free" : self.free_space,
		}
		self.transport.post("/builders/keepalive", data=data)

	@property
	def free_space(self):
		mp = system.get_mountpoint(BUILD_ROOT)

		return mp.space_left


class PakfireWorker(multiprocessing.Process):
	def __init__(self, config, waiting=None):
		multiprocessing.Process.__init__(self)

		# Save config.
		self.config = config

		# Waiting event. Clear if this worker is running a build.
		self.waiting = multiprocessing.Event()
		self.waiting.set()

		# Indicates if this worker is running.
		self.__running = True

	def run(self):
		# Register signal handlers.
		self.register_signal_handlers()

		# Create connection to the hub.
		self.transport = transport.PakfireHubTransport(self.config)
		self.transport.fork()

		while self.__running:
			# Try to get a new build job.
			job = self.get_new_build_job()
			if not job:
				continue

			# If we got a job, we are not waiting anymore.
			self.waiting.clear()

			# Run the job and return.
			return self.execute_job(job)

	def shutdown(self):
		self.__running = False

		# When we are just waiting, we can edit right away.
		if self.waiting.is_set():
			log.debug("Exiting immediately")
			sys.exit(1)

		# XXX figure out what to do, when a build is running.

	# Signal handling.

	def register_signal_handlers(self):
		signal.signal(signal.SIGCHLD, self.handle_SIGCHLD)
		signal.signal(signal.SIGINT,  self.handle_SIGTERM)
		signal.signal(signal.SIGTERM, self.handle_SIGTERM)

	def handle_SIGCHLD(self, signum, frame):
		"""
			Handle signal SIGCHLD.
		"""
		# Must be here so that SIGCHLD won't be propagated to
		# PakfireDaemon.
		pass

	def handle_SIGTERM(self, signum, frame):
		"""
			Handle signal SIGTERM.
		"""
		self.shutdown()

	def get_new_build_job(self, timeout=600):
		log.debug("Requesting new job...")

		try:
			job = self.transport.get_json("/builders/jobs/queue",
				data={ "timeout" : timeout, }, timeout=timeout)

			if job:
				return BuildJob(job)

		# As this is a long poll request, it is okay to time out.
		except TransportMaxTriesExceededError:
			pass

	def execute_job(self, job):
		log.debug("Executing job: %s" % job)

		# Call the function that processes the build and try to catch general
		# exceptions and report them to the server.
		# If everything goes okay, we tell this the server, too.
		try:
			# Create a temporary file and a directory for the resulting files.
			tmpdir  = tempfile.mkdtemp()
			tmpfile = os.path.join(tmpdir, os.path.basename(job.source_url))
			logfile = os.path.join(tmpdir, "build.log")

			# Create pakfire configuration instance.
			config = pakfire.config.ConfigDaemon()
			config.parse(job.config)

			# Create pakfire instance.
			p = None
			try:
				p = pakfire.base.PakfireBuilder(config=config, arch=job.arch)

				# Download the source package.
				grabber = pakfire.downloader.PackageDownloader(p)
				grabber.urlgrab(job.source_url, filename=tmpfile)

				# Check if the download checksum matches (if provided).
				if job.source_hash_sha512:
					h = hashlib.new("sha512")
					f = open(tmpfile, "rb")
					while True:
						buf = f.read(BUFFER_SIZE)
						if not buf:
							break

						h.update(buf)
					f.close()

					if not job.source_hash_sha512 == h.hexdigest():
						raise DownloadError, "Hash check did not succeed."

				# Create a new instance of a build environment.
				build = pakfire.builder.BuildEnviron(p, tmpfile,
					release_build=True, build_id=job.id, logfile=logfile)

				try:
					# Create the build environment.
					build.start()

					# Update the build status on the server.
					self.upload_buildroot(job, build.installed_packages)
					self.update_state(job, "running")

					# Run the build (without install test).
					build.build(install_test=False)

					# Copy the created packages to the tempdir.
					build.copy_result(tmpdir)

				finally:
					# Cleanup the build environment.
					build.stop()

				# Jippie, build is finished, we are going to upload the files.
				self.update_state(job, "uploading")

				# Walk through the result directory and upload all (binary) files.
				# Skip that for test builds.
				if not job.type == "test":
					for dir, subdirs, files in os.walk(tmpdir):
						for file in files:
							file = os.path.join(dir, file)
							if file in (logfile, tmpfile,):
								continue

							self.upload_file(job, file, "package")

			except DependencyError, e:
				message = "%s: %s" % (e.__class__.__name__, e)
				self.update_state(job, "dependency_error", message)
				raise

			except DownloadError, e:
				message = "%s: %s" % (e.__class__.__name__, e)
				self.update_state(job, "download_error", message)
				raise

			finally:
				if p:
					p.destroy()

				# Upload the logfile in any case and if it exists.
				if os.path.exists(logfile):
					self.upload_file(job, logfile, "log")

				# Cleanup the files we created.
				pakfire.util.rm(tmpdir)

		except DependencyError:
			# This has already been reported.
			raise

		except (DownloadError,):
			# Do not take any further action for these exceptions.
			pass

		except (KeyboardInterrupt, SystemExit):
			self.update_state(job, "aborted")

		except Exception, e:
			# Format the exception and send it to the server.
			message = "%s: %s" % (e.__class__.__name__, e)

			self.update_state(job, "failed", message)
			raise

		else:
			self.update_state(job, "finished")

	def update_state(self, job, state, message=None):
		"""
			Update state of the build job on the hub.
		"""
		data = {
			"message" : message or "",
		}

		self.transport.post("/builders/jobs/%s/state/%s" % (job.id, state),
			data=data)

	def upload_file(self, job, filename, type):
		assert os.path.exists(filename)
		assert type in ("package", "log")

		# First upload the file data and save the upload_id.
		upload_id = self.transport.upload_file(filename)

		data = {
			"type" : type,
		}

		# Add the file to the build.
		self.transport.post("/builders/jobs/%s/addfile/%s" % (job.id, upload_id),
			data=data)

	def upload_buildroot(self, job, installed_packages):
		pkgs = []
		for pkg in installed_packages:
			pkgs.append((pkg.friendly_name, pkg.uuid))

		data = { "buildroot" : json.dumps(pkgs) }

		self.transport.post("/builders/jobs/%s/buildroot" % job.id, data=data)
