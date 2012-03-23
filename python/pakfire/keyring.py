#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2012 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import datetime
import gpgme
import io
import os

import logging
log = logging.getLogger("pakfire")

from constants import *
from i18n import _
from system import system

class Keyring(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire
		
		# Configure the environment.
		os.environ["GNUPGHOME"] = self.path
		self.create_path()

	def __del__(self):
		del os.environ["GNUPGHOME"]

	@property
	def path(self):
		return KEYRING_DIR

	def create_path(self):
		filename = os.path.join(self.path, "gnupg.conf")

		if os.path.exists(filename):
			return

		if not os.path.exists(self.path):
			os.makedirs(self.path)
			# XXX chmod 700

		# Create a default gnupg.conf.
		f = open(filename, "w")
		f.write("# This is a default gnupg configuration file created by\n")
		f.write("# Pakfire %s.\n" % PAKFIRE_VERSION)
		f.close()
		# XXX chmod 600

	def init(self):
		log.info(_("Initializing local keyring..."))

		hostname, domainname = system.hostname.split(".", 1)

		self.gen_key(system.hostname, "%s@%s" % (hostname, domainname))

	def dump_key(self, keyfp):
		ret = []

		ctx = gpgme.Context()
		key = ctx.get_key(keyfp)

		for uid in key.uids:
			ret.append(uid.uid)

		ret.append("  " + _("Fingerprint: %s") % keyfp)
		ret.append("")

		for subkey in key.subkeys:
			ret.append("  " + _("Subkey: %s") % subkey.keyid)
			if subkey.expired:
				ret.append("    %s" % _("This key has expired!"))

			if subkey.secret:
				ret.append("    %s" % _("This is a secret key."))

			created = datetime.datetime.fromtimestamp(subkey.timestamp)
			ret.append("    %s" % _("Created: %s") % created)
			if subkey.expires:
				expires = datetime.datetime.fromtimestamp(subkey.expires)
				ret.append("    %s" % _("Expires: %s") % expires)
			else:
				ret.append("    %s" % _("This key does not expire."))

			if subkey.pubkey_algo == gpgme.PK_RSA:
				ret.append("    RSA/%s" % subkey.length)

			ret.append("")

		return ret

	def get_key(self, keyid):
		ctx = gpgme.Context()

		try:
			return ctx.get_key(keyid)
		except gpgme.GpgmeError:
			return None

	def gen_key(self, realname, email):
		params = """
			<GnupgKeyParms format="internal">
				Key-Type: RSA
				Key-Usage: sign
				Key-Length: 2048
				Name-Real: %s
				Name-Email: %s
				Expire-Date: 0
			</GnupgKeyParms>
		""" % (realname, email)

		# Create a new context.
		ctx = gpgme.Context()

		# Generate the key.
		result = ctx.genkey(params)

		# Return the fingerprint of the generated key.
		return result.fpr

	def import_key(self, keyfile):
		ret = []

		ctx = gpgme.Context()

		f = open(keyfile, "rb")
		res = ctx.import_(f)
		f.close()

		log.info(_("Successfully import key %s.") % keyfile)

	def export_key(self, keyid, keyfile):
		ctx = gpgme.Context()
		ctx.armor = True

		keydata = io.BytesIO()
		ctx.export(keyid, keydata)

		f = open(keyfile, "wb")
		f.write(keydata.getvalue())
		f.close()

	def delete_key(self, keyid):
		ctx = gpgme.Context()

		key = ctx.get_key(keyid)
		ctx.delete(key, True)

	def list_keys(self):
		ret = []

		ctx = gpgme.Context()

		keys = [k.subkeys[0].keyid for k in ctx.keylist(None, True)]

		for key in keys:
			ret += self.dump_key(key)

		return ret

	def sign(self, keyid, cleartext):
		ctx = gpgme.Context()
		ctx.armor = True

		key = ctx.get_key(keyid)
		ctx.signers = [key,]

		cleartext = io.BytesIO(cleartext)
		signature = io.BytesIO()

		ctx.sign(cleartext, signature, gpgme.SIG_MODE_DETACH)

		return signature.getvalue()

	def verify(self, signature, cleartext):
		# Create context.
		ctx = gpgme.Context()

		signature = io.BytesIO(signature)
		cleartext = io.BytesIO(cleartext)

		# Verify the data.
		sigs = ctx.verify(signature, cleartext, None)

		return sigs
