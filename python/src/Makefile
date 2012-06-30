
include ../../Makeconfig

# The name of the module.
MODULE_PAKFIRE = _pakfire.so
MODULE_LZMA    = _lzma.so
MODULES        = $(MODULE_PAKFIRE) $(MODULE_LZMA)

# Libs that are to be linked into the module.
MODULE_PAKFIRE_LIBS = -lcap -lpython$(PYTHON_VERSION) -lsolv
MODULE_LZMA_LIBS    = -llzma

SOURCES_LZMA     = _lzmamodule.c
SOURCES_PAKFIRE  = \
	capabilities.c  \
	_pakfiremodule.c  \
	problem.c \
	repo.c \
	solution.c \
	solver.c \
	transaction.c \
	pool.c \
	relation.c \
	request.c \
	solvable.c \
	step.c \
	util.c

OBJECTS_LZMA     = $(patsubst %.c,%.o,$(SOURCES_LZMA))
OBJECTS_PAKFIRE  = $(patsubst %.c,%.o,$(SOURCES_PAKFIRE))
OBJECTS          = $(OBJECTS_PAKFIRE) $(OBJECTS_LZMA)

.PHONY:
all: $(MODULES)

$(MODULE_PAKFIRE): $(OBJECTS_PAKFIRE)
	$(PYTHON_CC) $(PYTHON_CFLAGS) -shared $^ $(MODULE_PAKFIRE_LIBS) -o $@

$(MODULE_LZMA): $(OBJECTS_LZMA)
	$(PYTHON_CC) $(PYTHON_CFLAGS) -shared $^ $(MODULE_LZMA_LIBS) -o $@

%.o: %.c Makefile config.h
	$(PYTHON_CC) $(PYTHON_CFLAGS) -o $@ -c $<

.PHONY: clean
clean:
	rm -f $(OBJECTS) $(MODULES)

.PHONY: install
install: $(MODULES)
	-mkdir -pv $(DESTDIR)$(PYTHON_DIR)/$(PACKAGE_NAME)
	install -m 755 -v $(MODULE_PAKFIRE) $(DESTDIR)$(PYTHON_DIR)/$(PACKAGE_NAME)
	install -m 755 -v $(MODULE_LZMA) $(DESTDIR)$(PYTHON_DIR)/$(PACKAGE_NAME)
