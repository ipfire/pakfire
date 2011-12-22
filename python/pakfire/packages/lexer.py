#!/usr/bin/python

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

LEXER_DEFINITION      = re.compile(r"^([A-Za-z0-9_\-]+)\s*([\+\:])?=\s*(.+)?$")

LEXER_BLOCK_LINE_INDENT = "\t"
LEXER_BLOCK_LINE      = re.compile(r"^\t(.*)$")
LEXER_BLOCK_END       = re.compile(r"^end$")

LEXER_DEFINE_BEGIN    = re.compile(r"^(def)?\s?([A-Za-z0-9_\-]+)$")
LEXER_DEFINE_LINE     = LEXER_BLOCK_LINE
LEXER_DEFINE_END      = LEXER_BLOCK_END

LEXER_PACKAGE_BEGIN   = re.compile(r"^package ([A-Za-z0-9_\-\+\%\{\}]+)$")
LEXER_PACKAGE_LINE    = LEXER_BLOCK_LINE
LEXER_PACKAGE_END     = LEXER_BLOCK_END
LEXER_PACKAGE_INHERIT = re.compile(r"^template ([A-Z0-9]+)$")

LEXER_SCRIPTLET_BEGIN = re.compile(r"^script ([a-z]+)\s?(/[A-Za-z0-9\-\_/]+)?$")
LEXER_SCRIPTLET_LINE  = LEXER_BLOCK_LINE
LEXER_SCRIPTLET_END   = LEXER_BLOCK_END

LEXER_TEMPLATE_BEGIN  = re.compile(r"^template ([A-Z0-9]+)$")
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

LEXER_PACKAGES_BEGIN  = re.compile(r"^packages$")
LEXER_PACKAGES_LINE   = LEXER_BLOCK_LINE
LEXER_PACKAGES_END    = LEXER_BLOCK_END

LEXER_PACKAGE2_BEGIN  = re.compile(r"^package$")
LEXER_PACKAGE2_LINE   = LEXER_BLOCK_LINE
LEXER_PACKAGE2_END    = LEXER_BLOCK_END

LEXER_QUALITY_AGENT_BEGIN = re.compile(r"^quality-agent$")
LEXER_QUALITY_AGENT_LINE  = LEXER_BLOCK_LINE
LEXER_QUALITY_AGENT_END   = LEXER_BLOCK_END

# Statements:
LEXER_EXPORT          = re.compile(r"^export\s+([A-Za-z0-9_\-]+)\s*(\+)?=\s*(.+)?$")
LEXER_EXPORT2         = re.compile(r"^export\s+([A-Za-z0-9_\-]+)$")
LEXER_UNEXPORT        = re.compile(r"^unexport\s+([A-Za-z0-9_\-]+)$")
LEXER_INCLUDE         = re.compile(r"^include\s+(.+)$")

LEXER_VARIABLE        = re.compile(r"\%\{([A-Za-z0-9_\-]+)\}")
LEXER_SHELL           = re.compile(r"\%\(.*\)")

LEXER_IF_IF           = re.compile(r"^if\s+(.*)\s+(==|!=)\s+(.*)\s*")
LEXER_IF_ELIF         = re.compile(r"^elif\s+(.*)\s*(==|!=)\s*(.*)\s*")
LEXER_IF_ELSE         = re.compile(r"^else")
LEXER_IF_LINE         = LEXER_BLOCK_LINE
LEXER_IF_END          = LEXER_BLOCK_END

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
		"""
			Inherit everything from other lexer.
		"""
		self._definitions.update(other._definitions)

	@property
	def definitions(self):
		definitions = {}

		if self.parent:
			definitions.update(self.parent.definitions)

		definitions.update(self._definitions)

		return definitions

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

	def get_var(self, key, default=None, raw=False):
		definitions = {}
		definitions.update(self.root.definitions)
		if self.parent:
			definitions.update(self.parent.definitions)
		definitions.update(self.definitions)

		val = None
		try:
			val = definitions[key]
		except KeyError:
			pass

		if val is None:
			val = default

		if raw:
			return val

		return self.expand_string(val)

	def init(self, environ):
		pass

	def get_default_parsers(self):
		return [
			(LEXER_COMMENT,			self.parse_comment),
			(LEXER_DEFINITION,		self.parse_definition),
			(LEXER_DEFINE_BEGIN,	self.parse_define),
			(LEXER_IF_IF,			self.parse_if),
		]

	def get_parsers(self):
		return []

	def parse_line(self):
		# Skip empty lines.
		if self.line_is_empty():
			self._lineno += 1
			return

		line = self.get_line(self._lineno)

		parsers = self.get_parsers() + self.get_default_parsers()

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
			prev = self.get_var(k, default=None, raw=True)
			if prev:
				v = " ".join((prev or "", v))

		elif o == ":":
			# Expand the value immediately and save it.
			v = self.expand_string(v)

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

		# Check content of next line.
		found = None
		i = 1
		while True:
			line = self.get_line(self._lineno + i)

			# Skip empty lines.
			empty = re.match(LEXER_EMPTY_LINE, line)
			if empty:
				i += 1
				continue

			for pattern in (LEXER_DEFINE_LINE, LEXER_DEFINE_END):
				found = re.match(pattern, line)
				if found:
					break

			if found:
				break

		if found is None:
			line = self.get_line(self._lineno)
			raise LexerUnhandledLine, "%d: %s" % (self.lineno, line)

		# Go in to next line.
		self._lineno += 1

		key = m.group(2)
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

	def _parse_if_block(self, first=True):
		line = self.get_line(self._lineno)

		found = False

		if first:
			m = re.match(LEXER_IF_IF, line)
			if m:
				found = True
		else:
			m = re.match(LEXER_IF_ELIF, line)
			if m:
				found = True
			else:
				m = re.match(LEXER_IF_ELSE, line)
				if m:
					found = True

		if not found:
			raise LexerError, "No valid begin of if statement: %d: %s" \
					% (self.lineno, line)

		self._lineno += 1
		clause = m.groups()
		lines = []

		block_closed = False
		while len(self.lines) >= self._lineno:
			line = self.get_line(self._lineno)

			for pattern in (LEXER_IF_END, LEXER_IF_ELIF, LEXER_IF_ELSE):
				m = re.match(pattern, line)
				if m:
					block_closed = True
					break

			if block_closed:
				break

			m = re.match(LEXER_IF_LINE, line)
			if m:
				self._lineno += 1
				lines.append("%s" % m.groups())
				continue

			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				self._lineno += 1
				lines.append("")
				continue

			raise LexerUnhandledLine, "%d: %s" % (self.lineno, line)

		if not block_closed:
			raise LexerError, "Unclosed if block"

		return (clause, lines)

	def parse_if(self):
		blocks = []
		blocks.append(self._parse_if_block(first=True))

		while len(self.lines) >= self._lineno:
			line = self.get_line(self._lineno)

			found = False
			for pattern in (LEXER_IF_ELIF, LEXER_IF_ELSE,):
				m = re.match(pattern, line)
				if m:
					# Found another block.
					found = True
					blocks.append(self._parse_if_block(first=False))
					break

			if not found:
				break

		# Check for end.
		line = self.get_line(self._lineno)
		m = re.match(LEXER_IF_END, line)
		if not m:
			raise LexerError, "Unclosed if clause"

		self._lineno += 1

		# Read in all blocks, now we evaluate each clause.
		for clause, lines in blocks:
			val = False

			if len(clause) == 3:
				a, op, b = clause

				# Remove leading and trailing "s and 's.
				a = a.lstrip("\"'").rstrip("\"'")
				b = b.lstrip("\"'").rstrip("\"'")

				a = self.expand_string(a)
				b = self.expand_string(b)

				if op == "==":
					val = a == b
				elif op == "!=":
					val = not a == b
				else:
					raise LexerError, "Unknown operator: %s" % op

			else:
				# Else is always true.
				val = True

			# If any clause is true, we can parse the block.
			if val:
				lexer = self.__class__(lines, parent=self)
				self.inherit(lexer)
				break


class DefaultLexer(Lexer):
	"""
		A lexer which only knows about simple definitions.
	"""
	pass


class QualityAgentLexer(DefaultLexer):
	"""
		A lexer to read quality agent exceptions.
	"""
	@property
	def exports(self):
		exports = {}

		# Check if we permit full relro.
		if self.get_var("permit_not_full_relro"):
			exports["QUALITY_AGENT_PERMIT_NOT_FULL_RELRO"] = \
				self.get_var("permit_not_full_relro")

		# Check if we permit $ORIGIN in rpath.
		if self.get_var("rpath_allow_origin"):
			exports["QUALITY_AGENT_RPATH_ALLOW_ORIGIN"] = \
				self.get_var("rpath_allow_origin")

		# Load execstack whitelist.
		if self.get_var("whitelist_execstack"):
			exports["QUALITY_AGENT_WHITELIST_EXECSTACK"] = \
				self.get_var("whitelist_execstack")

		# Load nx whitelist.
		if self.get_var("whitelist_nx"):
			exports["QUALITY_AGENT_WHITELIST_NX"] = \
				self.get_var("whitelist_nx")

		# Load rpath whitelist.
		if self.get_var("whitelist_rpath"):
			exports["QUALITY_AGENT_WHITELIST_RPATH"] = \
				self.get_var("whitelist_rpath")

		# Load symlink whitelist
		if self.get_var("whitelist_symlink"):
			exports["QUALITY_AGENT_WHITELIST_SYMLINK"] = \
				self.get_var("whitelist_symlink")

		return exports


class TemplateLexer(DefaultLexer):
	def init(self, environ):
		# A place to store the scriptlets.
		self.scriptlets = {}

	def inherit(self, other):
		DefaultLexer.inherit(self, other)

		# Inherit all scriptlets.
		self.scriptlets.update(other.scriptlets)

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

	def get_scriptlet(self, name):
		return self.scriptlets.get(name, None)


class PackageLexer(TemplateLexer):
	def init(self, environ):
		TemplateLexer.init(self, environ)

		self._template = "MAIN"

		assert isinstance(self.parent, PackagesLexer) or \
			isinstance(self.parent, PackageLexer), self.parent

	@property
	def definitions(self):
		definitions = {}

		if self.parent:
			definitions.update(self.parent.definitions)

		if self.template:
			definitions.update(self.template.definitions)

		definitions.update(self._definitions)

		return definitions

	@property
	def template(self):
		if not self._template:
			return None

		# Get template from parent.
		try:
			return self.parent.templates[self._template]
		except KeyError:
			raise LexerError, "Template does not exist: %s" % self._template

	def get_parsers(self):
		parsers = [
			(LEXER_PACKAGE_INHERIT,		self.parse_inherit),
		] + TemplateLexer.get_parsers(self)

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

	def get_scriptlet(self, name):
		scriptlet = self.scriptlets.get(name, None)

		if scriptlet is None and self.template:
			scriptlet = self.template.get_scriptlet(name)

		if scriptlet and scriptlet["lang"] == "shell":
			scriptlet["scriptlet"] = \
				self.expand_string(scriptlet["scriptlet"])

		return scriptlet


class ExportLexer(DefaultLexer):
	@property
	def exports(self):
		if not hasattr(self.parent, "exports"):
			return self._exports

		exports = []
		for export in self._exports + self.parent.exports:
			exports.append(export)

		return exports

	def init(self, environ):
		# A list of variables that should be exported in the build
		# environment.
		self._exports = []
		self._unexports = []

	def get_parsers(self):
		return [
			(LEXER_EXPORT,			self.parse_export),
			(LEXER_EXPORT2,			self.parse_export2),
			(LEXER_UNEXPORT,		self.parse_unexport),
		]

	def inherit(self, other):
		DefaultLexer.inherit(self, other)

		# Try to remove all unexported variables.
		for unexport in other._unexports:
			try:
				self._exports.remove(unexport)
			except:
				pass

		for export in other._exports:
			if not export in self._exports:
				self._exports.append(export)

	def parse_export(self):
		k, v = self.parse_definition(pattern=LEXER_EXPORT)

		if k and not k in self.exports:
			self._exports.append(k)

	def parse_export2(self):
		line = self.get_line(self._lineno)
		self._lineno += 1

		m = re.match(LEXER_EXPORT2, line)
		if m:
			k = m.group(1)
			if k and k in self.exports:
				self._exports.append(k)

	def parse_unexport(self):
		line = self.get_line(self._lineno)
		self._lineno += 1

		m = re.match(LEXER_UNEXPORT, line)
		if m:
			k = m.group(1)
			if k and k in self.exports:
				self._exports.remove(k)
				self._unexports.append(k)


class BuildLexer(ExportLexer):
	@property
	def stages(self):
		return self.definitions


class RootLexer(ExportLexer):
	def init(self, environ):
		ExportLexer.init(self, environ)

		# Import all environment variables.
		if environ:
			for k, v in environ.items():
				self._definitions[k] = v

				self.exports.append(k)

		# Place for build instructions
		self.build = BuildLexer([], parent=self)

		# A place to store all packages and templates.
		# The parent of this is the build block because a lot
		# of relevant variables are set there and need to be used
		# later. That keeps us the root lexer a bit more clean.
		self.packages = PackagesLexer([], parent=self.build)

		# Place for quality-agent exceptions
		self.quality_agent = QualityAgentLexer([], parent=self)

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
		ExportLexer.inherit(self, other)

		self._definitions.update(other._definitions)

		self.build.inherit(other.build)
		self.packages.inherit(other.packages)
		self.quality_agent.inherit(other.quality_agent)

	@property
	def templates(self):
		return self.packages.templates

	def get_parsers(self):
		parsers = ExportLexer.get_parsers(self)
		parsers += [
			(LEXER_INCLUDE,			self.parse_include),
			(LEXER_PACKAGES_BEGIN,	self.parse_packages),
			(LEXER_BUILD_BEGIN,		self.parse_build),
			(LEXER_QUALITY_AGENT_BEGIN, self.parse_quality_agent),
		]

		return parsers

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

		build = BuildLexer(lines, parent=self.build)
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

	def parse_packages(self):
		keys, lines = self.read_block(
			pattern_start=LEXER_PACKAGES_BEGIN,
			pattern_line=LEXER_PACKAGES_LINE,
			pattern_end=LEXER_PACKAGES_END,
			raw=True,
		)

		pkgs = PackagesLexer(lines, parent=self.packages)
		self.packages.inherit(pkgs)

	def parse_quality_agent(self):
		keys, lines = self.read_block(
			pattern_start=LEXER_QUALITY_AGENT_BEGIN,
			pattern_line=LEXER_QUALITY_AGENT_LINE,
			pattern_end=LEXER_QUALITY_AGENT_END,
			raw = True,
		)

		qa = QualityAgentLexer(lines, parent=self.quality_agent)
		self.quality_agent.inherit(qa)


class PackagesLexer(DefaultLexer):
	def init(self, environ):
		# A place to store all templates.
		self._templates = {}

		# A place to store all packages.
		self.packages = []

	@property
	def templates(self):
		templates = {}

		if self.parent and hasattr(self.parent, "templates"):
			templates.update(self.parent.templates)

		templates.update(self._templates)

		return templates

	def inherit(self, other):
		DefaultLexer.inherit(self, other)

		# Copy all templates and packages but make sure
		# to update the parent lexer (for accessing each other).
		for name, template in other.templates.items():
			template.parent = self
			self._templates[name] = template

		for pkg in other.packages:
			pkg.parent = self
			self.packages.append(pkg)

	def __iter__(self):
		return iter(self.packages)

	def get_parsers(self):
		return [
			(LEXER_TEMPLATE_BEGIN,	self.parse_template),
			(LEXER_PACKAGE_BEGIN,	self.parse_package),
		]

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

		self._templates[name] = TemplateLexer(lines, parent=self)

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

		lines = ["_name = %s" % name]

		opened = False
		while len(self.lines) > self._lineno:
			line = self.get_line(self._lineno)

			m = re.match(LEXER_PACKAGE_END, line)
			if m:
				opened = False
				self._lineno += 1
				break

			m = re.match(LEXER_PACKAGE_LINE, line)
			if m:
				self._lineno += 1
				lines.append(m.group(1))
				opened = True
				continue

			# Accept empty lines.
			m = re.match(LEXER_EMPTY_LINE, line)
			if m:
				self._lineno += 1
				lines.append(line)
				continue

			# If there is an unhandled line in a block, we raise an error.
			if opened:
				raise Exception, "XXX unhandled line in package block: %s" % line

			# If the block was never opened, we just go on.
			else:
				break

		if opened:
			raise LexerError, "Unclosed package block '%s'." % name

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
