.PHONY: doc test lint format typecheck clean build wheel upload_test upload

doc:
	rm -rf docs/_build
	$(MAKE) -C docs html

test:
	pytest

lint:
	ruff check src tests
	ruff format --check src tests

format:
	ruff format src tests

typecheck:
	ty check

clean:
	rm -rf build dist src/*.egg-info

build: clean
	python -m build

# kept as an alias for muscle memory
wheel: build

upload_test: build
	twine check --strict dist/*
	twine upload --repository testpypi dist/*

upload: build
	twine check --strict dist/*
	twine upload dist/*
