#### workflow/docs.mk ---------------------------------------------------------

PYTHON ?= /storage/share/python/environments/Anaconda3/envs/labpy/bin/python

.PHONY: toc-all toc-issue toc-commit toc-daily toc-weekly toc-meeting toc-personal toc-idea

NOTIO := PYTHONPATH=src $(PYTHON) -m notio --root .

define MAKE_TOC_RULE
toc-$(1):
	@$(NOTIO) toc $(1)
.PHONY: toc-$(1)
endef

$(eval $(call MAKE_TOC_RULE,issue,issue,status,groupby=status))
$(eval $(call MAKE_TOC_RULE,commit,commit,title,))
$(eval $(call MAKE_TOC_RULE,daily,daily,,))
$(eval $(call MAKE_TOC_RULE,weekly,weekly,,))
$(eval $(call MAKE_TOC_RULE,meeting,meeting,participants,))
$(eval $(call MAKE_TOC_RULE,personal,personal,title))
$(eval $(call MAKE_TOC_RULE,idea,idea,title))

toc-all:
	@$(NOTIO) toc --all
