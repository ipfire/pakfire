
include Makeconfig

SUBDIRS = po python tools tools/fake-environ

all: build

.PHONY: build
build:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $${dir} || exit; \
	done

.PHONY: clean
clean:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $${dir} clean || exit; \
	done

.PHONY: dist
dist:
	git archive --format=tar --prefix=$(PACKAGE_NAME)-$(PACKAGE_VERSION)/ HEAD | \
		gzip -9 > $(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz

.PHONY: install
install: build
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $${dir} install || exit; \
	done

	-mkdir -pv $(DESTDIR)$(PREFIX)/lib/pakfire/macros
	cp -vf macros/*.macro $(DESTDIR)$(PREFIX)/lib/pakfire/macros

	# Install example configuration.
	-mkdir -pv $(DESTDIR)/etc/pakfire/repos
	for file in general.conf builder.conf client.conf daemon.conf distros; do \
		[ -e "$(DESTDIR)/etc/pakfire/$${file}" ] && continue; \
		cp -rvf examples/$${file} $(DESTDIR)/etc/pakfire/; \
	done

	# Install systemd file.
	-mkdir -pv $(DESTDIR)/usr/lib/systemd/system
	for file in $(UNIT_FILES); do \
		install -v -m 644 $${file} \
			$(DESTDIR)/usr/lib/systemd/system || exit 1; \
	done

.PHONY: check
check: all
	PYTHONPATH=python/src/ pylint -E python/pakfire

.PHONY: po
po:
	$(MAKE) -C po

.PHONY: pot
pot:
	$(MAKE) -C po pot
