
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
	-mkdir -pv $(DESTDIR)/etc/pakfire
	for file in general.conf builder.conf client.conf daemon.conf distros repos; do \
		[ -e "$(DESTDIR)/etc/pakfire/$${file}" ] && continue; \
		cp -rvf examples/$${file} $(DESTDIR)/etc/pakfire/; \
	done

.PHONY: check
check:
	./runpychecker.sh

.PHONY: po
po:
	$(MAKE) -C po
