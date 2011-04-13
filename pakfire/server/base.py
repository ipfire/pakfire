#!/usr/bin/python

import logging
import os
import socket
import xmlrpclib

import pakfire.packages

class MasterSlave(object):
	@property
	def hostname(self):
		"""
			Return the host's name.
		"""
		return socket.gethostname()

	def upload_package_file(self, source_id, pkg_id, pkg):
		logging.info("Adding package file: %s" % pkg.filename)

		# Read-in the package payload.
		f = open(pkg.filename, "rb")
		payload = xmlrpclib.Binary(f.read())
		f.close()

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
			"payload"     : payload,
		}

		if isinstance(pkg, pakfire.packages.BinaryPackage):
			info.update({
				"provides"    : " ".join(pkg.provides),
				"obsoletes"   : " ".join(pkg.obsoletes),
				"conflicts"   : " ".join(pkg.conflicts),
			})

		return self.conn.upload_package_file(pkg_id, info)

	def upload_log_file(self):
		pass # XXX TO BE DONE
