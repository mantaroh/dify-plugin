PY := python

.PHONY: validate invoke pack package clean

validate:
	$(PY) scripts/dev_cli.py validate

invoke:
	$(PY) scripts/dev_cli.py invoke --input '{"text":"hello"}'

pack:
	$(PY) scripts/dev_cli.py pack

package:
	$(PY) scripts/dev_cli.py package

clean:
	rm -rf dist
