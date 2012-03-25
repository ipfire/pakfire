#!/usr/bin/python

import os
import sys

import logging
log = logging.getLogger("pakfire")

try:
	from pakfire.cli import *
	from pakfire.i18n import _

except ImportError, e:
	# Catch ImportError and show a more user-friendly message about what
	# went wrong.

	# Try to load at least the i18n support, but when this fails as well we can
	# go with an English error message.
	try:
		from pakfire.i18n import _
	except ImportError:
		_ = lambda x: x

	# XXX Maybe we can make a more beautiful message here?!
	print _("There has been an error when trying to import one or more of the"
		" modules, that are required to run Pakfire.")
	print _("Please check your installation of Pakfire.")
	print
	print _("The error that lead to this:")
	print "  ", e
	print

	# Exit immediately.
	sys.exit(1)

basename2cls = {
	"pakfire"         : Cli,
	"pakfire-builder" : CliBuilder,
	"pakfire-client"  : CliClient,
	"pakfire-daemon"  : CliDaemon,
	"pakfire-key"     : CliKey,
	"pakfire-server"  : CliServer,
	"builder"         : CliBuilderIntern,
}

# Get the basename of the program
basename = os.path.basename(sys.argv[0])

# Check if the program was called with a weird basename.
# If so, we exit immediately.
if not basename2cls.has_key(basename):
	sys.exit(127)

# Return code for the shell.
ret = 0

try:
	# Creating command line interface
	cli = basename2cls[basename]()

	cli.run()

except KeyboardInterrupt:
	log.critical("Recieved keyboard interupt (Ctrl-C). Exiting.")
	ret = 1

# Catch all errors and show a user-friendly error message.
except Error, e:
	log.critical("")
	log.critical(_("An error has occured when running Pakfire."))
	log.error("")

	log.error(_("Error message:"))
	log.error("  %s: %s" % (e.__class__.__name__, e.message))
	log.error("")

	log.error(_("Further description:"))
	msg = "%s" % e
	for line in msg.splitlines():
		log.error("  %s" % line)
	log.error("")

	ret = e.exit_code

sys.exit(ret)

