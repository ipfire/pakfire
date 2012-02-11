
include ../Makeconfig

# Elfutils
LIBS_ELF = -lelf

# Beecrypt
LIBS_BEECRYPT = -lbeecrypt -lgomp

# popt
LIBS_POPT = -lpopt

SCRIPTS = $(SCRIPTS_BIN) $(SCRIPTS_SHELL)
SCRIPTS_BIN   = \
	debugedit

SCRIPTS_SHELL = \
	chroot-shell \
	cleanup \
	compress-man-pages \
	extract-debuginfo \
	find-common \
	find-provides \
	find-requires \
	pakfire-multicall.py \
	patch \
	py-compile \
	quality-agent \
	remove-static-libs \
	$(wildcard functions-*) \
	$(wildcard *.prov) \
	$(wildcard *.req)

.PHONY: all
all: $(SCRIPTS)

%.o: %.c Makefile
	$(CC) $(CFLAGS) -I. -o $@ -c $<

debugedit: debugedit.o hashtab.o
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS_BEECRYPT) $(LIBS_ELF) $(LIBS_POPT)

.PHONY: install
install: $(SCRIPTS)
	-mkdir -pv $(DESTDIR)$(SCRIPT_DIR)
	for file in $^; do \
		cp -vrf $${file} $(DESTDIR)$(SCRIPT_DIR)/ || exit; \
	done

	# Create script aliases.
	-mkdir -pv $(DESTDIR)/usr/bin
	ln -svf ../..$(SCRIPT_DIR)/pakfire-multicall.py $(DESTDIR)/usr/bin/pakfire
	ln -svf ../..$(SCRIPT_DIR)/pakfire-multicall.py $(DESTDIR)/usr/bin/pakfire-builder
	ln -svf ../..$(SCRIPT_DIR)/pakfire-multicall.py $(DESTDIR)/usr/bin/pakfire-client
	ln -svf ../..$(SCRIPT_DIR)/pakfire-multicall.py $(DESTDIR)/usr/bin/pakfire-daemon
	ln -svf ../..$(SCRIPT_DIR)/pakfire-multicall.py $(DESTDIR)/usr/bin/pakfire-key
	ln -svf ../..$(SCRIPT_DIR)/pakfire-multicall.py $(DESTDIR)/usr/bin/pakfire-server
	ln -svf pakfire-multicall.py                    $(DESTDIR)$(SCRIPT_DIR)/builder

	# Install QA.
	-mkdir -pv $(DESTDIR)/usr/lib/quality-agent
	cp -vf quality-agent.d/* $(DESTDIR)/usr/lib/quality-agent

.PHONY: clean
clean:
	: # Nothing yet to do
