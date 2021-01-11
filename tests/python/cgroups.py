#!/usr/bin/python3

import os
import unittest

import pakfire.cgroups as cgroups

class Test(unittest.TestCase):
	def setUp(self):
		# Find our own cgroup
		self.cgroup = cgroups.get_own_group()

	def test_find_own_group(self):
		"""
			Check if we found our own cgroup
		"""
		self.assertIsInstance(self.cgroup, cgroups.CGroup)

	def test_subgroup(self):
		# Create a new sub group
		subgroup = self.cgroup.create_subgroup("test-1")
		self.assertIsInstance(subgroup, cgroups.CGroup)

		# Attach the test process to it
		subgroup.attach_self()

		# Fetch pids
		pids = subgroup.pids

		# There must be one pid in this list
		self.assertTrue(len(pids) == 1)

		# The pid must be the one of this process
		self.assertTrue(pids[0] == os.getpid())

		# Can't really test killing ourselves here
		#subgroup.killall()

		# Destroy it
		subgroup.destroy()


if __name__ == "__main__":
	unittest.main()
