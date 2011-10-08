#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
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

import hashlib
import logging
import os
import random
import socket
import subprocess
import tempfile
import time
import xmlrpclib

import pakfire.api
import pakfire.base
import pakfire.config
import pakfire.downloader
import pakfire.packages
import pakfire.repository
import pakfire.util

from pakfire.constants import *

CHUNK_SIZE = 1024**2 # 1M

class Source(object):
	def __init__(self, pakfire, id, name, url, path, targetpath, revision, branch):
		self.pakfire = pakfire
		self.id = id
		self.name = name
		self.url = url
		self.targetpath = targetpath
		self.revision = revision
		self.branch = branch

		# If the repository is not yet checked out, we create a local clone
		# from it to work with it.
		if not self.is_cloned():
			self.clone()
		else:
			# Always refresh the repository to have the recent commits.
			self.fetch()

	def is_cloned(self):
		return os.path.exists(self.path)

	def clone(self):
		if self.is_cloned():
			return

		dirname = os.path.dirname(self.path)
		basename = os.path.basename(self.path)

		if not os.path.exists(dirname):
			os.makedirs(dirname)

		self._git("clone %s %s" % (self.url, basename), path=dirname)

	def fetch(self):
		self._git("fetch")

	@property
	def path(self):
		h = hashlib.sha1(self.url)

		# XXX path is to be changed
		return "/var/cache/pakfire/sources/%s" % h.hexdigest()

	def _git(self, cmd, path=None):
		if not path:
			path = self.path

		cmd = "cd %s && git %s" % (path, cmd)

		logging.debug("Running command: %s" % cmd)

		return subprocess.check_output(["/bin/sh", "-c", cmd])

	def _git_changed_files(self, revision1, revision2=""):
		files = self._git("diff --name-only %s %s" % (revision1, revision2))

		return [os.path.join(self.path, f) for f in files.splitlines()]

	def _git_checkout_revision(self, revision):
		self._git("checkout %s" % revision)

	def update_revision(self, revision, **pakfire_args):
		# Checkout the revision we want to work with.
		self._git_checkout_revision(revision)

		# Get list of all changes files between the current revision and
		# the previous one.
		files = self._git_changed_files("HEAD^", "HEAD")

		# Update all changed files and return a repository with them.
		return self.update_files([f for f in files if f.endswith(".%s" % MAKEFILE_EXTENSION)],
			**pakfire_args)

	def update_files(self, files, **pakfire_args):
		rnd = random.randint(0, 1024**2)
		tmpdir = "/tmp/pakfire-source-%s" % rnd

		pkgs = []
		for file in files:
			if os.path.exists(file):
				pkgs.append(file)
			# XXX not sure what to do here
			#else:
			#	pkg_name = os.path.basename(os.path.dirname(file))
			#
			#	# Send deleted package to server.
			#	self.master.package_remove(self, pkg_name)

		if not pkgs:
			return

		# XXX This totally ignores the local configuration.
		pakfire.api.dist(pkgs, resultdirs=[tmpdir,], **pakfire_args)

		# Create a kind of dummy repository to link the packages against it.
		if pakfire_args.has_key("build_id"):
			del pakfire_args["build_id"]
		pakfire_args["mode"] = "server"

		repo = pakfire.api.repo_create("source-%s" % rnd, [tmpdir,], type="source",
			**pakfire_args)

		return repo

	def update_all(self):
		_files = []
		for dir, subdirs, files in os.walk(self.path):
			for f in files:
				if not f.endswith(".%s" % MAKEFILE_EXTENSION):
					continue

				_files.append(os.path.join(dir, f))

		return self.update_files(_files)


class XMLRPCTransport(xmlrpclib.Transport):
	user_agent = "pakfire/%s" % PAKFIRE_VERSION

	def single_request(self, *args, **kwargs):
		ret = None

		# Tries can be passed to this method.
		tries = kwargs.pop("tries", 100)

		while tries:
			try:
				ret = xmlrpclib.Transport.single_request(self, *args, **kwargs)

			except socket.error, e:
				# These kinds of errors are not fatal, but they can happen on
				# a bad internet connection or whatever.
				#   32 Broken pipe
				#  110 Connection timeout
				#  111 Connection refused
				if not e.errno in (32, 110, 111,):
					raise

			except xmlrpclib.ProtocolError, e:
				# Log all XMLRPC protocol errors.
				logging.error("XMLRPC protocol error:")
				logging.error("  URL: %s" % e.url)
				logging.error("  HTTP headers:")
				for header in e.headers.items():
					logging.error("    %s: %s" % header)
				logging.error("  Error code: %s" % e.errcode)
				logging.error("  Error message: %s" % e.errmsg)
				raise

			else:
				# If request was successful, we can break the loop.
				break

			# If the request was not successful, we wait a little time to try
			# it again.
			logging.debug("Request was not successful, we wait a little bit and try it again.")
			time.sleep(30)
			tries -= 1

		else:
			logging.error("Maximum number of tries was reached. Giving up.")
			# XXX need better exception here.
			raise Exception, "Could not fulfill request."

		return ret


class Server(object):
	def __init__(self, **pakfire_args):
		self.config = pakfire.config.Config()

		server = self.config._slave.get("server")

		logging.info("Establishing RPC connection to: %s" % server)

		self.conn = xmlrpclib.ServerProxy(server, transport=XMLRPCTransport(),
			allow_none=True)

		self.pakfire_args = pakfire_args

	@property
	def hostname(self):
		"""
			Return the host's name.
		"""
		return socket.gethostname()

	def update_info(self):
		# Get the current load average.
		loadavg = ", ".join(["%.2f" % l for l in os.getloadavg()])

		# Get all supported architectures.
		arches = sorted([a for a in self.config.supported_arches])
		arches = " ".join(arches)

		# Determine CPU model
		cpuinfo = {}
		with open("/proc/cpuinfo") as f:
			for line in f.readlines():
				# Break at an empty line, because all information after that
				# is redundant.
				if not line:
					break

				try:
					key, value = line.split(":")
				except:
					pass # Skip invalid lines

				key, value = key.strip(), value.strip()

				cpuinfo[key] = value

		cpu_model = cpuinfo.get("model name", "Could not be determined")

		# Determine memory size
		memory = 0
		with open("/proc/meminfo") as f:
			line = f.readline()

			try:
				a, b, c = line.split()
			except:
				pass
			else:
				memory = int(b)

		self.conn.update_host_info(loadavg, cpu_model, memory, arches)

	def upload_file(self, filename, build_id):
		# Get the hash of the file.
		hash = pakfire.util.calc_hash1(filename)

		# Get the size of the file.
		size = os.path.getsize(filename)

		# Get an upload ID from the server.
		upload_id = self.conn.get_upload_cookie(os.path.basename(filename),
			size, hash)

		# Calculate the number of chunks.
		chunks = (size / CHUNK_SIZE) + 1

		# Cut the file in pieces and upload them one after another.
		with open(filename) as f:
			chunk = 0
			while True:
				data = f.read(CHUNK_SIZE)
				if not data:
					break

				chunk += 1
				logging.info("Uploading chunk %s/%s of %s." % (chunk, chunks,
					os.path.basename(filename)))

				data = xmlrpclib.Binary(data)
				self.conn.upload_chunk(upload_id, data)

		# Tell the server, that we finished the upload.
		ret = self.conn.finish_upload(upload_id, build_id)

		# If the server sends false, something happened with the upload that
		# could not be recovered.
		if not ret:
			raise Exception, "Upload failed."

	def update_build_status(self, build_id, status, message=""):
		ret = self.conn.update_build_state(build_id, status, message)

		# If the server returns False, then it did not acknowledge our status
		# update and the build has to be aborted.
		if not ret:
			raise BuildAbortedException, "The build was aborted by the master server."

	def build_job(self, type=None):
		build = self.conn.build_job() # XXX type=None

		# If the server has got no job for us, we end right here.
		if not build:
			return

		job_types = {
			"binary" : self.build_binary_job,
			"source" : self.build_source_job,
		}

		build_id   = build["id"]
		build_type = build["type"]

		try:
			func = job_types[build_type]
		except KeyError:
			raise Exception, "Build type not supported: %s" % type

		# Call the function that processes the build and try to catch general
		# exceptions and report them to the server.
		# If everything goes okay, we tell this the server, too.
		try:
			func(build_id, build)

		except DependencyError:
			# This has already been reported by func.
			raise

		except Exception, e:
			# Format the exception and send it to the server.
			message = "%s: %s" % (e.__class__.__name__, e)

			self.update_build_status(build_id, "failed", message)
			raise

		else:
			self.update_build_status(build_id, "finished")

	def build_binary_job(self, build_id, build):
		arch     = build["arch"]
		filename = build["name"]
		download = build["download"]
		hash1    = build["hash1"]

		# Create a temporary file and a directory for the resulting files.
		tmpdir = tempfile.mkdtemp()
		tmpfile = os.path.join(tmpdir, filename)
		logfile = os.path.join(tmpdir, "build.log")

		# Get a package grabber and add mirror download capabilities to it.
		grabber = pakfire.downloader.PackageDownloader(self.config)

		try:
			# Download the source.
			grabber.urlgrab(download, filename=tmpfile)

			# Check if the download checksum matches.
			if pakfire.util.calc_hash1(tmpfile) == hash1:
				print "Checksum matches: %s" % hash1
			else:
				raise DownloadError, "Download was corrupted"

			# Update the build status on the server.
			self.update_build_status(build_id, "running")

			# Run the build.
			pakfire.api.build(tmpfile, build_id=build_id,
				resultdirs=[tmpdir,], logfile=logfile)

			self.update_build_status(build_id, "uploading")

			# Walk through the result directory and upload all (binary) files.
			for dir, subdirs, files in os.walk(tmpdir):
				for file in files:
					file = os.path.join(dir, file)
					if file in (logfile, tmpfile,):
						continue

					self.upload_file(file, build_id)

		except DependencyError, e:
			message = "%s: %s" % (e.__class__.__name__, e)
			self.update_build_status(build_id, "dependency_error", message)
			raise

		finally:
			# Upload the logfile in any case and if it exists.
			if os.path.exists(logfile):
				self.upload_file(logfile, build_id)

			# Cleanup the files we created.
			pakfire.util.rm(tmpdir)

	def build_source_job(self, build_id, build):
		# Update the build status on the server.
		self.update_build_status(build_id, "running")

		source = Source(self, **build["source"])

		repo = source.update_revision(build["revision"], build_id=build_id,
			**self.pakfire_args)

		try:
			# Upload all files in the repository.
			for pkg in repo:
				path = os.path.join(pkg.repo.path, pkg.filename)
				self.upload_file(path, build_id)
		finally:
			repo.remove()

	def update_repositories(self, limit=2):
		repos = self.conn.get_repos(limit)

		for repo in repos:
			files = self.conn.get_repo_packages(repo["id"])

			for arch in repo["arches"]:
				path = "/pakfire/repositories/%s/%s/%s" % \
					(repo["distro"]["sname"], repo["name"], arch)

				pakfire.api.repo_create(path, files)
