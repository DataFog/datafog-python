# Iw want to create a script that basically runs: setup.py sdist bdist_wheel and then deploys the package to pypi
# I want to be able to run this script from the root of the project
# when I run the script, I want to be able to pass in the version number as an argument

# I want to be able to run the script like this:
# ./deploy.sh 0.0.1

# I want to be able to run the script without any arguments and it should prompt me for the version number

# I want to be able to run the script with the -h or --help flag and it should print out a help message


python setup.py sdist bdist_wheel
twine upload dist/*
rm -rf build dist datafog_python.egg-info
