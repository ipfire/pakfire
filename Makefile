
DESTDIR ?= /

all: po build

.PHONY: build
build:
	python setup.py build

.PHONY: clean
clean:
	python setup.py clean
	-rm -rfv build

.PHONY: dist
dist:
	python setup.py sdist

.PHONY: install
install: po
	python setup.py install  --root $(DESTDIR)

	-mkdir -pv $(DESTDIR)/etc/pakfire.repos.d
	cp -vf examples/pakfire.conf $(DESTDIR)/etc/pakfire.conf
	cp -vf examples/pakfire.repos.d/* $(DESTDIR)/etc/pakfire.repos.d/

.PHONY: check
check:
	./runpychecker.sh

.PHONY: po
po:
	find pakfire src scripts -name "*.py" -or -name "*.c" -or -name "pakfire" -and -type f | \
		grep -v "__version__.py" | sort > po/POTFILES.in
