#### workflow/notes.mk --------------------------------------------------------

OWNER ?= $(shell whoami)
DATE  ?= $(shell date +%F)
NOTIO := PYTHONPATH=src $(PYTHON) -m notio --root .

YEAR := $(shell $(PYTHON) -c "from datetime import date; print(date.fromisoformat('$(DATE)').strftime('%Y'))")
WEEK := $(shell $(PYTHON) -c "from datetime import date; print(date.fromisoformat('$(DATE)').strftime('%V'))")

.PHONY: note-daily note-weekly

note-daily:
	@$(NOTIO) note daily --owner "$(OWNER)" --date "$(DATE)" --title "Daily $(DATE)"

note-weekly:
	@$(NOTIO) note weekly --owner "$(OWNER)" --date "$(DATE)" --title "Week $(YEAR)-W$(WEEK)"

EVENT_TYPES := personal idea commit issue meeting

.PHONY: $(EVENT_TYPES:%=note-%)
$(EVENT_TYPES:%=note-%):
	@TYPE=$(patsubst note-%,%,$@); \
	if [ -n "$(TITLE)" ]; then \
		$(NOTIO) note "$$TYPE" --owner "$(OWNER)" --date "$(DATE)" --title "$(TITLE)"; \
	else \
		$(NOTIO) note "$$TYPE" --owner "$(OWNER)" --date "$(DATE)"; \
	fi
