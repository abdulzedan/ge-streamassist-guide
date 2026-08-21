# Gemini Enterprise — Stream Assist guide
# Common entry points; every target is safe to re-run.

.PHONY: help env discover smoke smoke-full python-deps clean

help:
	@echo "make env         - create .env from the template (edit it after)"
	@echo "make discover    - list your apps and agents (uses .env or: make discover PROJECT=my-proj)"
	@echo "make smoke       - run the fast snippet smoke suite against your app"
	@echo "make smoke-full  - smoke suite including deep research plan + media generation"
	@echo "make python-deps - install the python client dependencies"

env:
	@test -f .env && echo ".env already exists - not overwriting" || (cp .env.example .env && echo "created .env - edit PROJECT_ID/LOCATION/APP_ID (or run make discover PROJECT=...)")

discover:
	./scripts/discover.sh $(PROJECT)

smoke:
	./scripts/run-all.sh

smoke-full:
	./scripts/run-all.sh --full

python-deps:
	pip install -r snippets/python/requirements.txt

clean:
	rm -f generated.png video.mp4 image.png

.PHONY: setup node-example
setup:
	./scripts/setup-env.sh $(PROJECT)

node-example:
	cd snippets/node && node example.mjs "$(Q)"
