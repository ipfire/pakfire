#!/usr/bin/python

import logging
import os
import random
import string

import depsolve
import distro
import logger
import packages
import transaction
import util

from config import Config
from constants import *
from distro import Distribution
from errors import BuildError, PakfireError
from repository import Repositories
from i18n import _

__version__ = PAKFIRE_VERSION

class Pakfire(object):
	def __init__(self, builder=False, configs=[], disable_repos=None,
			distro_config=None):
		# Check if we are operating as the root user.
		self.check_root_user()

		# The path where we are operating in.
		if builder:
			self.builder = True
			self.path = os.path.join(BUILD_ROOT, util.random_string())
		else:
			self.builder = False
			self.path = "/"

			# XXX check if we are actually running on an ipfire system.

		# Read configuration file(s)
		self.config = Config(pakfire=self)
		for filename in configs:
			self.config.read(filename)

		# Setup the logger
		logger.setup_logging(self.config)
		self.config.dump()

		# Get more information about the distribution we are running
		# or building
		self.distro = Distribution(self, distro_config)
		self.repos  = Repositories(self)

		# XXX Disable repositories if passed on command line
		#if disable_repos:
		#	for repo in disable_repos:
		#		self.repos.disable_repo(repo)

		# Update all indexes of the repositories (not force) so that we will
		# always work with valid data.
		self.repos.update()

	def destroy(self):
		if not self.path == "/":
			util.rm(self.path)

	@property
	def supported_arches(self):
		return self.distro.supported_arches

	def check_root_user(self):
		if not os.getuid() == 0 or not os.getgid() == 0:
			raise Exception, "You must run pakfire as the root user."

	def check_build_mode(self):
		"""
			Check if we are running in build mode.
			Otherwise, raise an exception.
		"""
		if not self.builder:
			raise BuildError, "Cannot build when not in build mode."

	def check_host_arch(self, arch):
		"""
			Check if we can build for arch.
		"""

		# If no arch was given on the command line we build for our
		# own arch which should always work.
		if not arch:
			return True

		if not self.distro.host_supports_arch(arch):
			raise BuildError, "Cannot build for the target architecture: %s" % arch

		raise BuildError, arch
