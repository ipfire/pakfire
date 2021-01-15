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

	def test_return_value(self):
		with self.assertRaises(pakfire.CommandExecutionError) as e:
			self.pakfire.execute(["/bin/sh", "-c", "exit 123"])

		# Extract return code
		code, = e.exception.args

		self.assertTrue(code == 123)

	def test_execute_non_existant_command(self):
		"""
			Executing non-existant commands should raise an error
		"""
		with self.assertRaises(pakfire.CommandExecutionError):
			self.pakfire.execute(["/usr/bin/does-not-exist"])

	def test_execute_output(self):
		self.pakfire.execute(["/bin/bash", "--help"], log_output=True)

	# This is an interactive test which cannot be performed automatically
	#def test_shell(self):
	#	self.pakfire.execute(["/bin/bash", "-i"])


if __name__ == "__main__":
	unittest.main()
