#!/usr/bin/python

import logging
import os
import re

from pakfire.constants import *

class LexerError(Exception):
	pass


class LexerUnhandledLine(LexerError):
	pass


class EndOfFileError(LexerError):
	pass


class LexerUndefinedVariableError(LexerError):
	pass


LEXER_VALID_PACKAGE_NAME    = re.compile(r"[A-Za-z][A-Za-z0-9\_\-\+]")

# XXX need to build check
LEXER_VALID_SCRIPTLET_NAME  = re.compile(r"((pre|post|posttrans)(in|un|up))")

LEXER_COMMENT_CHAR    = "#"
LEXER_COMMENT         = re.compile(r"^\s*#")
LEXER_QUOTES          = "\"'"
LEXER_EMPTY_LINE      = re.compile(r"^\s*$")

LEXER_DEFINITION      = re.compile(r"^([A-Za-z0-9_\-]+)\s*(\+)?=\s*(.+)?")

LEXER_BLOCK_LINE_INDENT = "\t"
LEXER_BLOCK_LINE      = re.compile(r"^\t(.*)$")
LEXER_BLOCK_END       = re.compile(r"^end$")

LEXER_DEFINE_BEGIN    = re.compile(r"^def ([A-Za-z0-9_\-]+)$")
LEXER_DEFINE_LINE     = LEXER_BLOCK_LINE
LEXER_DEFINE_END      = LEXER_BLOCK_END

LEXER_PACKAGE_BEGIN   = re.compile(r"^package ([A-Za-z0-9_\-\+\%\{\}]+)$")
LEXER_PACKAGE_LINE    = LEXER_BLOCK_LINE
LEXER_PACKAGE_END     = LEXER_BLOCK_END
LEXER_PACKAGE_INHERIT = re.compile(r"^template ([A-Z]+)$")

LEXER_SCRIPTLET_BEGIN = re.compile(r"^script ([a-z]+)\s?(/[A-Za-z0-9\-\_/]+)?$")
LEXER_SCRIPTLET_LINE  = LEXER_BLOCK_LINE
LEXER_SCRIPTLET_END   = LEXER_BLOCK_END

LEXER_TEMPLATE_BEGIN  = re.compile(r"^template ([A-Z]+)$")
LEXER_TEMPLATE_LINE   = LEXER_BLOCK_LINE
LEXER_TEMPLATE_END    = LEXER_BLOCK_END

LEXER_BUILD_BEGIN     = re.compile(r"^build$")
LEXER_BUILD_LINE      = LEXER_BLOCK_LINE
LEXER_BUILD_END       = LEXER_BLOCK_END

LEXER_DEPS_BEGIN      = re.compile(r"^dependencies$")
LEXER_DEPS_LINE       = LEXER_BLOCK_LINE
LEXER_DEPS_END        = LEXER_BLOCK_END

LEXER_DISTRO_BEGIN    = re.compile(r"^distribution$")
LEXER_DISTRO_LINE     = LEXER_BLOCK_LINE
LEXER_DISTRO_END      = LEXER_BLOCK_END

LEXER_PACKAGE2_BEGIN  = re.compile(r"^package$")
LEXER_PACKAGE2_LINE   = LEXER_BLOCK_LINE
LEXER_PACKAGE2_END    = LEXER_BLOCK_END

# Statements:
LEXER_EXPORT          = re.compile(r"^export ([A-Za-z0-9_\-])\s*(\+)?=\s*(.+)$")
LEXER_UNEXPORT        = re.compile(r"^unexport ([A-Za-z0-9_\-]+)$")
LEXER_INCLUDE         = re.compile(r"^include (.+)$")

LEXER_VARIABLE        = re.compile(r"\%\{([A-Za-z0-9_\-]+)\}")


class Lexer(object):
	def __init__(self, lines=[], parent=None, environ=None):
		self.lines = lines
		self.parent = parent

		self._lineno = 0

		# A place to store all definitions.
		self._definitions = {}

		# Init function that can be overwritten by child classes.
		self.init(environ)

		# Run the parser.
		self.run()

	def inherit(self, other):
		self._definitions.update(other._definitions)

	@property
	def definitions(self):
		return self._definitions

	@classmethod
	def open(cls, filename, *args, **kwargs):
		f = open(filename)
		lines = f.readlines()
		f.close()

		return cls(lines, *args, **kwargs)

	@property
	def lineno(self):
		return self._lineno + 1

	@property
	def root(self):
		if self.parent:
			return self.parent.root

		return self

	def get_line(self, no, raw=False):
		try:
			line = self.lines[no]
		except KeyError:
			raise EndOfFileError

		# Strip newline.
		line = line.rstrip("\n")
		
		# DEBUG
		#print line

		if raw:
			return line

		# strip comments - caution: quotations

		if line.startswith(LEXER_COMMENT_CHAR):
			return ""

		# XXX fix removing of comments in lines
		#i = -1
		#length = len(line)
		#quote = None

		#for i in range(length):
		#	s = line[i]

		#	if s in LEXER_QUOTES:
		#		if quote == s:
		#			quote = None
		#		else:
		#			quote = s

		#	if s == LEXER_COMMENT_CHAR:
		#		return line[:i+1]

		return line

	def line_is_empty(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_EMPTY_LINE, line)
		if m:
			return True

		return False

	def expand_string(self, s):
		if s is None:
			return ""

		while s:
			m = re.search(LEXER_VARIABLE, s)
			if not m:
				break

			var = m.group(1)
			s = s.replace("%%{%s}" % var, self.get_var(var))

		return s

	def get_var(self, key, default=None):
		definitions = {}
		definitions.update(self.root.definitions)
		definitions.update(self.definitions)

		val = None
		try:
			val = definitions[key]
		except KeyError:
			logging.warning("Undefined variable: %s" % key)
			#if default is None:
			#	logging.warning("Undefined variable: %s" % key)
			#	raise LexerUndefinedVariableError, key

		if val is None:
			val = default

		return self.expand_string(val)

	def init(self, environ):
		pass

	def get_default_parsers(self):
		return [
			(LEXER_COMMENT,			self.parse_comment),
			(LEXER_DEFINITION,		self.parse_definition),
			(LEXER_DEFINE_BEGIN,	self.parse_define),
		]

	def get_parsers(self):
		return []

	def parse_line(self):
		# Skip empty lines.
		if self.line_is_empty():
			self._lineno += 1
			return

		line = self.get_line(self._lineno)

		parsers = self.get_default_parsers() + self.get_parsers()

		found = False
		for pattern, func in parsers:
			m = re.match(pattern, line)
			if m:
				# Hey, I found a match, we parse it with the subparser function.
				found = True
				func()

				break

		if not found:
			raise LexerUnhandledLine, "%d: %s" % (self.lineno, line)

	def read_block(self, pattern_start=None, pattern_line=None, pattern_end=None,
			raw=False):
		assert pattern_start
		assert pattern_line
		assert pattern_end

		line = self.get_line(self._lineno)

		m = re.match(pattern_start, line)
		if not m:
			raise LexerError

		# Go in to next line.
		self._lineno += 1

		groups = m.groups()

		lines = []
		while True:
			line = self.get_line(self._lineno, raw=raw)

			m = re.match(pattern_end, line)
			if m:
				self._lineno += 1
				break

			m = re.match(pattern_line, line)
			if m:
				lines.append(m.group(1))
				self._lineno += 1
				continue

			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				lines.append("")
				self._lineno += 1
				continue

			if not line.startswith(LEXER_BLOCK_LINE_INDENT):
				raise LexerError, "Line has not the right indentation: %d: %s" \
					% (self.lineno, line)

			raise LexerUnhandledLine, "%d: %s" % (self.lineno, line)

		return (groups, lines)

	def run(self):
		while self._lineno < len(self.lines):
			self.parse_line()

	def parse_comment(self):
		line = self.get_line(self._lineno)

		if not line:
			return

		raise LexerUnhandledLine, "%d: %s" % (self.lineno, line)

	def parse_definition(self, pattern=LEXER_DEFINITION):
		line = self.get_line(self._lineno)

		m = re.match(pattern, line)
		if not m:
			raise LexerError, "Not a definition: %s" % line

		# Line was correctly parsed, can go on.
		self._lineno += 1

		k, o, v = m.groups()

		if o == "+":
			prev = self.definitions.get(k, None)
			if prev is None and self.parent:
				prev = self.parent.definitions.get(k, None)
			if prev:
				v = " ".join((prev or "", v))

		# Handle backslash.
		while v and v.endswith("\\"):
			line = self.get_line(self._lineno)
			self._lineno += 1

			v = v[:-1] + line

		self._definitions[k] = v

		return k, v

	def parse_define(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_DEFINE_BEGIN, line)
		if not m:
			raise Exception, "XXX not a define"

		# Go in to next line.
		self._lineno += 1

		key = m.group(1)
		assert key

		value = []
		while True:
			line = self.get_line(self._lineno)		

			m = re.match(LEXER_DEFINE_END, line)
			if m:
				self._lineno += 1
				break

			m = re.match(LEXER_DEFINE_LINE, line)
			if m:
				self._lineno += 1
				value.append(m.group(1))
				continue

			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				self._lineno += 1
				value.append("")
				continue

			raise LexerError, "Unhandled line: %s" % line

		self._definitions[key] = "\n".join(value)


class DefaultLexer(Lexer):
	"""
		A lexer which only knows about about simple definitions and def.
	"""
	pass


class TemplateLexer(DefaultLexer):
	def init(self, environ):
		# A place to store the scriptlets.
		self.scriptlets = {}

	@property
	def definitions(self):
		definitions = {}

		assert self.parent
		definitions.update(self.parent.definitions)
		definitions.update(self._definitions)

		return definitions

	def get_parsers(self):
		return [
			(LEXER_SCRIPTLET_BEGIN,	self.parse_scriptlet),
		]

	def parse_scriptlet(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_SCRIPTLET_BEGIN, line)
		if not m:
			raise Exception, "Not a scriptlet"

		self._lineno += 1

		name = m.group(1)

		# check if scriptlet was already defined.
		if self.scriptlets.has_key(name):
			raise Exception, "Scriptlet %s is already defined" % name

		path = m.group(2)
		if path:
			self.scriptlets[name] = {
				"lang" : "bin",
				"path" : self.expand_string(path),
			}
			return

		lines = []
		while True:
			line = self.get_line(self._lineno, raw=True)

			m = re.match(LEXER_SCRIPTLET_END, line)
			if m:
				self._lineno += 1
				break

			m = re.match(LEXER_SCRIPTLET_LINE, line)
			if m:
				lines.append(m.group(1))
				self._lineno += 1
				continue

			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				lines.append("")
				self._lineno += 1
				continue

			raise LexerUnhandledLine, "%d: %s" % (self.lineno, line)

		self.scriptlets[name] = {
			"lang"      : "shell",
			"scriptlet" : "\n".join(lines),
		}


class PackageLexer(TemplateLexer):
	def init(self, environ):
		TemplateLexer.init(self, environ)

		self._template = "MAIN"

	@property
	def definitions(self):
		definitions = {}

		if self.template:
			definitions.update(self.template.definitions)

		definitions.update(self._definitions)

		return definitions

	@property
	def template(self):
		if not self._template:
			return None

		# Get templates from root.
		assert self.root
		templates = self.root.templates

		try:
			return templates[self._template]
		except KeyError:
			raise LexerError, "Template does not exist: %s" % self._template

	def get_parsers(self):
		parsers = TemplateLexer.get_parsers(self)

		parsers += [
			(LEXER_PACKAGE_INHERIT,		self.parse_inherit),
		]

		return parsers

	def parse_inherit(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_PACKAGE_INHERIT, line)
		if not m:
			raise LexerError, "Not a template inheritance: %s" % line

		self._lineno += 1

		self._template = m.group(1)

		# Check if template exists.
		assert self.template


class BuildLexer(DefaultLexer):
	@property
	def definitions(self):
		return self._definitions

	@property
	def stages(self):
		return self.definitions

	def inherit(self, other):
		"""
			Inherit everything from other lexer.
		"""
		self._definitions.update(other._definitions)


class RootLexer(DefaultLexer):
	def init(self, environ):
		# A list of variables that should be exported in the build
		# environment.
		self.exports = []

		# Import all environment variables.
		if environ:
			for k, v in environ.items():
				self._definitions[k] = v

				self.exports.append(k)

		# A place to store all packages.
		self.packages = []

		# A place to store all templates.
		self.templates = {}

		# Place for build instructions
		self.build = BuildLexer([], parent=self)

		# Include all macros.
		if not self.parent:
			for macro in MACRO_FILES:
				self.include(macro)

	def include(self, file):
		# Create a new lexer, and parse the whole file.
		include = RootLexer.open(file, parent=self)

		# Copy all data from the included file.
		self.inherit(include)

	def inherit(self, other):
		"""
			Inherit everything from other lexer.
		"""
		self._definitions.update(other._definitions)

		self.build.inherit(other.build)
		self.templates.update(other.templates)
		self.packages += other.packages

		for export in other.exports:
			if not export in self.exports:
				self.exports.append(export)

	def get_parsers(self):
		return [
			(LEXER_INCLUDE,			self.parse_include),
			(LEXER_TEMPLATE_BEGIN,	self.parse_template),
			(LEXER_PACKAGE_BEGIN,	self.parse_package),
			(LEXER_BUILD_BEGIN,		self.parse_build),
		]

	def parse_build(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_BUILD_BEGIN, line)
		if not m:
			raise LexerError, "Not a build statement: %s" % line

		self._lineno += 1

		lines = []

		while True:
			line = self.get_line(self._lineno)

			m = re.match(LEXER_BUILD_END, line)
			if m:
				self._lineno += 1
				break

			m = re.match(LEXER_BUILD_LINE, line)
			if m:
				lines.append(m.group(1))
				self._lineno += 1

			# Accept empty lines.
			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				lines.append(line)
				self._lineno += 1
				continue

		build = BuildLexer(lines, parent=self)
		self.build.inherit(build)

	def parse_include(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_INCLUDE, line)
		if not m:
			raise LexerError, "Not an include statement: %s" % line

		# Get the filename from the line.
		file = m.group(1)
		file = self.expand_string(file)

		# Include the content of the file.
		self.include(file)

		# Go on to next line.
		self._lineno += 1

	def parse_export(self):
		k, v = self.parse_definition(pattern, LEXER_EXPORT)

		if k and not k in self.exports:
			self.exports.append(k)

	def parse_unexport(self):
		line = self.get_line(self._lineno)
		self._lineno += 1

		m = re.match(LEXER_UNEXPORT, line)
		if m:
			k = m.group(1)
			if k and k in self.exports:
				self.exports.remove(k)

	def parse_template(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_TEMPLATE_BEGIN, line)
		if not m:
			raise Exception, "Not a template"

		# Line was correctly parsed, can go on.
		self._lineno += 1

		name = m.group(1)
		lines = []

		while True:
			line = self.get_line(self._lineno)

			m = re.match(LEXER_TEMPLATE_END, line)
			if m:
				self._lineno += 1
				break

			m = re.match(LEXER_TEMPLATE_LINE, line)
			if m:
				lines.append(m.group(1))
				self._lineno += 1

			# Accept empty lines.
			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				lines.append(line)
				self._lineno += 1
				continue

		template = TemplateLexer(lines, parent=self)
		self.templates[name] = template

	def parse_package(self):
		line = self.get_line(self._lineno)

		m = re.match(LEXER_PACKAGE_BEGIN, line)
		if not m:
			raise Exception, "Not a package: %s" %line

		self._lineno += 1

		name = m.group(1)
		name = self.expand_string(name)

		m = re.match(LEXER_VALID_PACKAGE_NAME, name)
		if not m:
			raise LexerError, "Invalid package name: %s" % name

		lines = ["name = %s" % name]

		while True:
			line = self.get_line(self._lineno)

			m = re.match(LEXER_PACKAGE_END, line)
			if m:
				self._lineno += 1
				break

			m = re.match(LEXER_PACKAGE_LINE, line)
			if m:
				self._lineno += 1
				lines.append(m.group(1))
				continue

			# Accept empty lines.
			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				self._lineno += 1
				lines.append(line)
				continue

			raise Exception, "XXX unhandled line in package block: %s" % line

		package = PackageLexer(lines, parent=self)
		self.packages.append(package)


class FileLexer(DefaultLexer):
	def init(self, environ):
		self.build = DefaultLexer()
		self.deps = DefaultLexer()
		self.distro = DefaultLexer()
		self.package = DefaultLexer()

	def get_parsers(self):
		return [
			(LEXER_BUILD_BEGIN,		self.parse_build),
			(LEXER_DISTRO_BEGIN,	self.parse_distro),
			(LEXER_PACKAGE2_BEGIN,	self.parse_package),
			(LEXER_DEPS_BEGIN,		self.parse_deps),
		]

	def parse_build(self):
		keys, lines = self.read_block(
			pattern_start=LEXER_BUILD_BEGIN,
			pattern_line=LEXER_BUILD_LINE,
			pattern_end=LEXER_BUILD_END,
			raw=True,
		)

		build = DefaultLexer(lines)
		self.build.inherit(build)

	def parse_distro(self):
		keys, lines = self.read_block(
			pattern_start=LEXER_DISTRO_BEGIN,
			pattern_line=LEXER_DISTRO_LINE,
			pattern_end=LEXER_DISTRO_END,
			raw=True,
		)

		distro = DefaultLexer(lines)
		self.distro.inherit(distro)

	def parse_package(self):
		keys, lines = self.read_block(
			pattern_start=LEXER_PACKAGE2_BEGIN,
			pattern_line=LEXER_PACKAGE2_LINE,
			pattern_end=LEXER_PACKAGE2_END,
			raw=True,
		)

		pkg = DefaultLexer(lines)
		self.package.inherit(pkg)

	def parse_deps(self):
		keys, lines = self.read_block(
			pattern_start=LEXER_DEPS_BEGIN,
			pattern_line=LEXER_DEPS_LINE,
			pattern_end=LEXER_DEPS_END,
			raw=True,
		)

		deps = DefaultLexer(lines)
		self.deps.inherit(deps)
