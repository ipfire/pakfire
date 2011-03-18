#!/usr/bin/python

import os
import tarfile

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.progress import TextMeter

import packager

from base import Package
from source import SourcePackage
from virtual import VirtualPackage
from pakfire.errors import DownloadError
from pakfire.constants import *

class SourceDownloader(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire

		self.grabber = URLGrabber(
			prefix = self.pakfire.config.get("source_download_url"),
			progress_obj = TextMeter(),
			quote = 0,
		)

	def download(self, filename):
		filename = os.path.join(SOURCE_CACHE_DIR, filename)

		if os.path.exists(filename):
			return filename

		dirname = os.path.dirname(filename)
		if not os.path.exists(dirname):
			os.makedirs(dirname)

		try:
			self.grabber.urlgrab(os.path.basename(filename), filename=filename)
		except URLGrabError, e:
			raise DownloadError, "%s %s" % (os.path.basename(filename), e)

		return filename


class MakeVirtualPackage(VirtualPackage):
	"""
		A simple package that always overwrites the file_patterns.
	"""
	@property
	def file_patterns(self):
		"""
			All files that belong into a source package are located in /build.
		"""
		return ["/",]

class Makefile(Package):
	def __init__(self, pakfire, filename):
		Package.__init__(self, pakfire)
		self.filename = filename

	@property
	def files(self):
		basedir = os.path.dirname(self.filename)

		for dirs, subdirs, files in os.walk(basedir):
			for f in files:
				yield os.path.join(dirs, f)

	def extract(self, env):
		# Copy all files that belong to the package
		for f in self.files:
			_f = f[len(os.path.dirname(self.filename)):]
			env.copyin(f, "/build/%s" % _f)

		downloader = SourceDownloader(env.pakfire)
		for filename in env.make_sources():
			_filename = downloader.download(filename)

			if _filename:
				env.copyin(_filename, "/build/files/%s" % os.path.basename(_filename))

	@property
	def package_filename(self):
		return PACKAGE_FILENAME_FMT % {
			"arch"    : self.arch,
			"ext"     : PACKAGE_EXTENSION,
			"name"    : self.name,
			"release" : self.release,
			"version" : self.version,
		}

	@property
	def arch(self):
		"""
			This is only used to create the name of the source package.
		"""
		return "src"

	def dist(self, env):
		"""
			Create a source package in env.

			We assume that all requires files are in /build.
		"""
		pkg = MakeVirtualPackage(self.pakfire, env.make_info)

		p = packager.SourcePackager(self.pakfire, pkg, env)
		p()

