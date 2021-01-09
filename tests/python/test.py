#!/usr/bin/python3

import unittest

class Test(unittest.TestCase):
	"""
		This is an example test for Pakfire
	"""
	def test_example(self):
		self.assertEqual("ABC", "ABC")

if __name__ == "__main__":
	unittest.main()
