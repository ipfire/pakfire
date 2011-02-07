#!/usr/bin/python

import os
import tarfile

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.progress import TextMeter

import packager
import pakfire.repository as repository

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


class Makefile(Package):
	def __init__(self, pakfire, filename):
		repo = repository.DummyRepository(pakfire)

		Package.__init__(self, pakfire, repo)
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
		basedir = env.chrootPath("build")

		files = {
			"data.img" : env.chrootPath("tmp/data.img"),
			"signature" : env.chrootPath("tmp/signature"),
			"info" : env.chrootPath("tmp/info"),
		}

		# Package all files.
		a = tarfile.open(files["data.img"], "w")
		for dir, subdirs, _files in os.walk(basedir):
			for file in _files:
				file = os.path.join(dir, file)

				a.add(file, arcname=file[len(basedir):])
		a.close()

		# XXX add compression for the sources

		# Create an empty signature.
		f = open(files["signature"], "w")
		f.close()

		pkg = VirtualPackage(self.pakfire, env.make_info)

		# Save meta information.
		f = open(files["info"], "w")
		f.write(SOURCE_PACKAGE_META % {
			"PKG_NAME" : pkg.name,
		})
		f.close()

		result = env.chrootPath("result", "src", pkg.filename)
		resultdir = os.path.dirname(result)
		if not os.path.exists(resultdir):
			os.makedirs(resultdir)

		f = tarfile.open(result, "w")
		for arcname, name in files.items():
			f.add(name, arcname=arcname, recursive=False)

		f.close()

