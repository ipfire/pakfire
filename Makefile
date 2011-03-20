
DESTDIR ?= /

all: build

.PHONY: build
build:
	python setup.py build

.PHONY: clean
clean:
	python setup.py clean

.PHONY: dist
dist:
	python setup.py sdist

.PHONY: install
install:
	python setup.py install  --root $(DESTDIR)

	-mkdir -pv $(DESTDIR)/etc/pakfire.repos.d
	cp -vf examples/pakfire.conf $(DESTDIR)/etc/pakfire.conf
	cp -vf examples/pakfire.repos.d/* $(DESTDIR)/etc/pakfire.repos.d/

.PHONY: check
check:
	./runpychecker.sh
