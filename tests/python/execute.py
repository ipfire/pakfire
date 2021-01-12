#!/usr/bin/python3

import pakfire
import unittest

class Test(unittest.TestCase):
	"""
		This tests the execute command
	"""
	def setUp(self):
		self.pakfire = pakfire.Pakfire("/")

	def test_execute(self):
		r = self.pakfire.execute(["/usr/bin/sleep", "0"])

		self.assertIsNone(r)

	def test_environ(self):
		r = self.pakfire.execute(["/bin/sh", "-c", "echo ${VAR1}"],
			environ={"VAR1" : "VAL1"})

		self.assertIsNone(r)

	def test_invalid_inputs(self):
		# Arguments
		with self.assertRaises(TypeError):
			self.pakfire.execute("/usr/bin/sleep")

		with self.assertRaises(TypeError):
			self.pakfire.execute(["/usr/bin/sleep", 1])

		with self.assertRaises(TypeError):
			self.pakfire.execute(("/usr/bin/sleep", "--help"))

		# Environment
		with self.assertRaises(TypeError):
			self.pakfire.execute(["/usr/bin/sleep", "--help"], environ={"VAR1" : 1})

		with self.assertRaises(TypeError):
			self.pakfire.execute(["/usr/bin/sleep", "--help"], environ={1 : "VAL1"})

		with self.assertRaises(TypeError):
			self.pakfire.execute(["/usr/bin/sleep", "--help"], environ="VAR1=VAL1")

	def test_execute_non_existant_command(self):
		"""
			Executing non-existant commands should raise an error
		"""
		with self.assertRaises(pakfire.CommandExecutionError):
			self.pakfire.execute(["/usr/bin/does-not-exist"])

	# This is an interactive test which cannot be performed automatically
	#def test_shell(self):
	#	self.pakfire.execute(["/bin/bash", "-i"])


if __name__ == "__main__":
	unittest.main()