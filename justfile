version := `python3 -c "from datafog.__about__ import __version__; print(__version__)"`

default:
	@echo "\"just publish\"?"

tag:
	@if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then exit 1; fi
	curl -H "Authorization: token `cat ~/.github-access-token`" -d '{"tag_name": "v{{version}}"}' https://api.github.com/repos/datafog/datafog-python/releases

upload: clean
	@if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then exit 1; fi
	# https://stackoverflow.com/a/58756491/353337
	python3 -m build --sdist --wheel .
	twine upload dist/*

publish: tag upload

clean:
	@find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
	@rm -rf datafog/*.egg-info/ build/ dist/ .tox/

format:
	isort . 
	black . 
	blacken-docs README.md 

lint:
	black --check . 
	flake8 . 
