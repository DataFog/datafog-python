version := `python -c "from datafog.__about__ import __version__; print(__version__)"`

# Set the virtual environment path
venv_dir := ".venv"
python := venv_dir + "/bin/python"
pip := venv_dir + "/bin/pip"

# Default recipe
default:
    @echo "Available commands:"
    @echo "  just setup    - Set up the development environment"
    @echo "  just format   - Format the code"
    @echo "  just lint     - Lint the code"
    @echo "  just test     - Run tests"
    @echo "  just clean    - Clean up build artifacts"
    @echo "  just publish  - Publish the package"

# Set up the development environment
setup:
    python -m venv {{venv_dir}}
    {{pip}} install -e ".[dev]"
    {{pip}} install isort black blacken-docs flake8 tox

# Format the code
format:
    {{python}} -m isort .
    {{python}} -m black .
    {{python}} -m blacken_docs README.md

# Lint the code
lint:
    {{python}} -m black --check .
    {{python}} -m flake8 .

# Run tests
test:
    {{python}} -m tox

# Clean up build artifacts
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    rm -rf datafog/*.egg-info/ build/ dist/ .tox/

# Tag a new release
tag:
    @if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
        echo "Error: Not on main branch"; \
        exit 1; \
    fi
    curl -H "Authorization: token `cat ~/.github-access-token`" \
         -d '{"tag_name": "v{{version}}"}' \
         https://api.github.com/repos/datafog/datafog-python/releases

# Upload the package to PyPI
upload: clean
    @if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then \
        echo "Error: Not on main branch"; \
        exit 1; \
    fi
    {{python}} -m build --sdist --wheel .
    {{python}} -m twine upload dist/*

# Publish the package (tag and upload)
publish: tag upload