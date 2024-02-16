

python setup.py sdist bdist_wheel
twine upload dist/*
rm -rf build dist datafog_python.egg-info
