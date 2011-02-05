#!/usr/bin/python

import logging
import os

from ConfigParser import ConfigParser

import base

from constants import *

class Config(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire

		self._config = {
			"debug" : True,
			"logfile" : "/var/log/pakfire.log",
			"source_download_url" : SOURCE_DOWNLOAD_URL,
		}

		self._config_repos = {}
		self._distro = {}
		self._files = []

		# Read default configuration files
		for file in self.config_files:
			self.read(file)

	def dump(self):
		logging.debug("Configuration:")
		for k, v in self._config.items():
			logging.debug(" %s : %s" % (k, v))

		logging.debug("Loaded from files:")
		for f in self._files:
			logging.debug(" %s" % f)

	def read(self, filename):
		# If filename does not exist we return silently
		if not os.path.exists(filename):
			return

		filename = os.path.abspath(filename)

		# If the file was already loaded, we return silently, too
		if filename in self._files:
			return

		logging.debug("Reading configuration file: %s" % filename)

		config = ConfigParser()
		config.read(filename)

		# Read the main section from the file if any
		if "main" in config.sections():
			for k,v in config.items("main"):
				self._config[k] = v
			config.remove_section("main")

		# Read distribution information from the file
		if "distro" in config.sections():
			for k,v in config.items("distro"):
				self._distro[k] = v
			config.remove_section("distro")

		# Read repository definitions
		for section in config.sections():
			if not self._config_repos.has_key(section):
				self._config_repos[section] = {}

			options = {}
			for option in config.options(section):
				options[option] = config.get(section, option)

			self._config_repos[section].update(options)

		self._files.append(filename)

	def get(self, key, default=None):
		return self._config.get(key, default)

	def set(self, key, val):
		self._config[key] = val

	def get_repos(self):
		return self._config_repos.items()

	@property
	def config_files(self):
		files = []

		if self.pakfire.builder:
			path = os.getcwd()

			while not path == "/":
				_path = os.path.join(path, "config")
				if os.path.exists(_path):
					break

				_path = None
				path = os.path.dirname(path)

			if _path:
				files.append(os.path.join(_path, "pakfire.conf"))
				files.append(os.path.join(_path, "default.conf"))

			# Remove non-existant files
			for f in files:
				if not os.path.exists(f):
					files.remove(f)

		if not files:
			# Return system configuration files
			files += [CONFIG_FILE]
			files += [os.path.join(CONFIG_DIR, f) for f in os.listdir(CONFIG_DIR)]

		return files

