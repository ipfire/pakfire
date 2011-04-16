#!/usr/bin/python

import hashlib
import logging
import os
import socket
import xmlrpclib

import pakfire.packages

CHUNK_SIZE = 2097152 # 2M

class MasterSlave(object):
	@property
	def hostname(self):
		"""
			Return the host's name.
		"""
		return socket.gethostname()

	def _chunked_upload(self, filename):
		# Update the amount of chunks that there will be to be uploaded.
		chunks = (os.path.getsize(filename) / CHUNK_SIZE) + 1

		# Open the file for read.
		f = open(filename, "rb")

		chunk, id = 0, ""
		while True:
			# Read a chunk and break if we reached the end of the file.
			data = f.read(CHUNK_SIZE)
			if not data:
				break

			chunk += 1
			logging.info("Uploading chunk %s/%s of %s." % (chunk, chunks, filename))

			# Calc the hash of the chunk.
			hash = hashlib.sha1(data)

			# Actually do the upload and make sure we got an ID.
			id = self.conn.chunk_upload(id, hash.hexdigest(), xmlrpclib.Binary(data))
			assert id

		f.close()

		return id

	def upload_package_file(self, source_id, pkg_id, pkg):
		logging.info("Uploading package file: %s" % pkg.filename)

		# Upload the file at first to the server.
		file_id = self._chunked_upload(pkg.filename)

		info = {
			"filename"    : os.path.basename(pkg.filename),
			"source_id"   : source_id,
			"type"        : pkg.type,
			"arch"        : pkg.arch,
			"summary"     : pkg.summary,
			"description" : pkg.description,
			"requires"    : " ".join(pkg.requires),
			"provides"    : "",
			"obsoletes"   : "",
			"conflicts"   : "",
			"url"         : pkg.url,
			"license"     : pkg.license,
			"maintainer"  : pkg.maintainer,
			"size"        : pkg.size,
			"hash1"       : pkg.hash1,
			"build_host"  : pkg.build_host,
			"build_id"    : pkg.build_id,
			"build_time"  : pkg.build_time,
			"uuid"        : pkg.uuid,
		}

		if isinstance(pkg, pakfire.packages.BinaryPackage):
			info.update({
				"provides"    : " ".join(pkg.provides),
				"obsoletes"   : " ".join(pkg.obsoletes),
				"conflicts"   : " ".join(pkg.conflicts),
			})

		return self.conn.package_add_file(pkg_id, file_id, info)

	def upload_log_file(self):
		pass # XXX TO BE DONE
