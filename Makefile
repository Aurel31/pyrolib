doc:
    rm -r docs/_build
    cd docs && make html

test:
    pytest #--cov=nobvisual 

lint:
    pylint src/pyrolib

wheel:
    rm -rf build
    rm -rf dist
    python setup.py sdist bdist_wheel

upload_test:
    twine upload --repository-url https://test.pypi.org/pyrolib/ dist/*

upload:
    twine upload dist/*
