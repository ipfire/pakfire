#!/usr/bin/python

import sys

import packager

from file import FilePackage

class BinaryPackage(FilePackage):
	type = "bin"

	@property
	def arch(self):
		return self.metadata.get("PKG_ARCH")

	@property
	def requires(self):
		ret = ""

		for i in ("PKG_REQUIRES", "PKG_DEPS"):
			ret = self.metadata.get(i, ret)
			if ret:
				break

		return ret.split()

	@property
	def provides(self):
		return self.metadata.get("PKG_PROVIDES").split()

	def get_extractor(self, pakfire):
		return packager.Extractor(pakfire, self)


if __name__ == "__main__":
	for pkg in sys.argv[1:]:
		pkg = BinaryPackage(pkg)

		fmt = "%-10s : %s"

		items = (
			("Name", pkg.name),
			("Version", pkg.version),
			("Release", pkg.release),
			("Epoch", pkg.epoch),
			("Size", pkg.size),
			("Arch", pkg.arch),
			("Signature", pkg.signature),
		)

		for item in items:
			print fmt % item

		print fmt % ("Filelist", "")
		print "\n".join([" %s" % f for f in pkg.filelist])
		
		print pkg.filelist

		print

