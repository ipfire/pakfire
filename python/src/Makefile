
include ../../Makeconfig

# The name of the module.
MODULENAME = _pakfire.so

# Libs that are to be linked into the module.
MODULELIBS = -lpython$(PYTHON_VERSION) -lsolv -lsolvext

SOURCES = $(wildcard *.c)
OBJECTS = $(patsubst %.c,%.o,$(SOURCES))

.PHONY:
all: $(MODULENAME)

$(MODULENAME): $(OBJECTS)
	$(PYTHON_CC) $(PYTHON_CFLAGS) -shared $^ $(MODULELIBS) -o $@

%.o: %.c Makefile
	$(PYTHON_CC) $(PYTHON_CFLAGS) -o $@ -c $<

.PHONY: clean
clean:
	rm -f $(OBJECTS) $(MODULENAME)

.PHONY: install
install: $(MODULENAME)
	-mkdir -pv $(DESTDIR)$(PYTHON_DIR)/$(PACKAGE_NAME)
	cp -vf $< $(DESTDIR)$(PYTHON_DIR)/$(PACKAGE_NAME)/
