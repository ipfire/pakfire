#!/usr/bin/python

import random
import sys
import time

def fork_builder(*args, **kwargs):
	cb = ClientBuilder(*args, **kwargs)

	try:
		cb()
	except Exception, e:
		print e
		sys.exit(1)

class ClientBuilder(object):
	def __init__(self, id):
		self.id = id

	def __call__(self, *args):
		print "Running", self.id, args

		time.sleep(2)

		if random.choice((False, False, False, True)):
			raise Exception, "Process died"


import multiprocessing


processes = []

while True:
	# Check if there are at least 2 processes running.
	if len(processes) < 2:
		process = multiprocessing.Process(target=fork_builder, args=(len(processes),))

		process.daemon = True
		process.start()

		processes.append(process)

	print len(processes), "in process list:", processes

	for process in processes:
		time.sleep(0.5)

		print process.name, "is alive?", process.is_alive()

		if not process.is_alive():
			print "Removing process", process
			print "  Exitcode:", process.exitcode
			processes.remove(process)
