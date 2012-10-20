
include ../Makeconfig

POT_FILE = $(PACKAGE_NAME).pot
PO_FILES = $(wildcard *.po)
MO_FILES = $(patsubst %.po,%.mo,$(PO_FILES))
LANGS    = $(patsubst %.po,%,$(PO_FILES))

TRANS_FILES := $(addprefix $(TOP),$(TRANS_FILES))
TRANS_FILES := $(sort $(wildcard $(TRANS_FILES)))

.PHONY: all
all: $(MO_FILES)

.PHONY: pot
pot: $(POT_FILE)

$(POT_FILE): $(TRANS_FILES)
	xgettext -d $(PACKAGE_NAME) -k_ -kN_ \
		-o $@ --add-comments --from-code=UTF-8 $^ 

%.mo: %.po
	msgfmt -o $@ $<

.PHONY: install
install: $(MO_FILES)
	# Install all language catalogs to their designated place.
	for lang in $(LANGS); do \
		mkdir -pv $(DESTDIR)/usr/share/locale/$${lang}/LC_MESSAGES/; \
		cp -vf $${lang}.mo $(DESTDIR)/usr/share/locale/$${lang}/LC_MESSAGES/$(PACKAGE_NAME).mo || exit; \
	done

.PHONY: clean
clean:
	rm -f $(MO_FILES)
