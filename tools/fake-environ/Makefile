
include ../../Makeconfig

LIB = libpakfire_preload.so

SOURCES = $(wildcard *.c)
OBJECTS = $(patsubst %.c,%.o,$(SOURCES))

.PHONY: all
all: $(LIB)

%.o: %.c Makefile
	$(CC) $(CFLAGS) -o $@ -c $<

$(LIB): $(OBJECTS)
	$(CC) $(CFLAGS) -shared -o $@ $? -ldl

.PHONY: install
install: all
	-mkdir -pv $(DESTDIR)$(LIBDIR)
	install -p -m 755 $(LIB) $(DESTDIR)$(LIBDIR)

.PHONY: clean
clean:
	$(LIB)
