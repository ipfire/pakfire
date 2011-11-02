
include ../Makeconfig

SCRIPTS = $(SCRIPTS_BIN) $(SCRIPTS_SHELL)
SCRIPTS_BIN   =
SCRIPTS_SHELL = \
	chroot-shell \
	cleanup \
	dependency-tracker \
	pakfire-multicall.py \
	py-compile \
	quality-agent \
	remove-static-libs \
	$(wildcard functions-*) \
	$(wildcard *.prov) \
	$(wildcard *.req)

.PHONY: all
all: $(SCRIPTS)

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
	ln -svf ../..$(SCRIPT_DIR)/pakfire-multicall.py $(DESTDIR)/usr/bin/pakfire-server
	ln -svf pakfire-multicall.py                    $(DESTDIR)$(SCRIPT_DIR)/builder

	# Install QA.
	-mkdir -pv $(DESTDIR)/usr/lib/quality-agent
	cp -vf quality-agent.d/* $(DESTDIR)/usr/lib/quality-agent

.PHONY: clean
clean:
	: # Nothing yet to do
