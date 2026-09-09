# Gemini Enterprise — Stream Assist guide
# Common entry points; every target is safe to re-run.

.PHONY: help env discover smoke smoke-full python-deps clean

help:
	@echo "make soak-*      - 24h reliability soak test on Cloud Run (see soak/README.md)"
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

# ---- 24h soak test (soak/) --------------------------------------------
.PHONY: soak-deploy soak-start soak-stop soak-status soak-run soak-report soak-local
soak-deploy:      ## build image, create Cloud Run jobs + schedulers (paused)
	./soak/deploy.sh deploy
soak-start:       ## start a campaign: make soak-start HOURS=24 PROFILE=standard
	./soak/deploy.sh start $(or $(HOURS),24) $(or $(PROFILE),standard)
soak-stop:
	./soak/deploy.sh stop
soak-status:
	./soak/deploy.sh status
soak-run:         ## execute one job now: make soak-run TIER=fast|heavy|report
	./soak/deploy.sh run $(or $(TIER),fast)
soak-report:      ## render + download the campaign report: make soak-report LABEL=final
	./soak/deploy.sh report $(or $(LABEL),final)
soak-local:       ## run the fast tier once from this machine (needs .venv + ADC), results in soak/out/
	cd soak && set -a && . ../.env && set +a && SSL_CERT_FILE=/etc/ssl/cert.pem REQUESTS_CA_BUNDLE=/etc/ssl/cert.pem \
	  ../.venv/bin/python -m soak --local out run --tier fast --all --ignore-campaign
