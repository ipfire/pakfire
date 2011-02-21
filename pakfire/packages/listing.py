#!/usr/bin/python

import logging

class PackageListing(object):
	def __init__(self, packages=[]):
		self.__packages = []

		if packages:
			for package in packages:
				self.__packages.append(package)

		self.__packages.sort()

	def __repr__(self):
		return "<PackageListing (%d) %s>" % (len(self.__packages),
			[p.friendly_name for p in self.__packages])

	def __iter__(self):
		return iter(self.__packages)

	def __len__(self):
		return len(self.__packages)

	def get_by_name(self, name):
		for pkg in self.__packages:
			if pkg.name == name:
				yield pkg

	def get_most_recent(self):
		if self.__packages:
			return self.__packages[-1]

	def unique(self):
		pkgs = []

		for pkg in self.__packages:
			if pkg in pkgs:
				continue

			pkgs.append(pkg)

		self.__packages = pkgs

