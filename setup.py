#  package using pip, navigate to the directory that contains the setup.py file and type pip install .
from setuptools import setup, find_packages



# Read README for the long description
with open('README.md', 'r') as f:
    long_description = f.read()


setup(
    name='datafog',
    version='1.4.0',  
    packages=find_packages(),  
    author='Sid Mohan',
    author_email='sid@datafog.ai',
    description='Scan & Redact PII before uploading to RAG apps',
    long_description=long_description,
    long_description_content_type='text/markdown', 
    install_requires=['faker', 'pandas', 'sqlalchemy'],
    classifiers=[
        'License :: OSI Approved :: MIT License',  # Choose a license
        'Programming Language :: Python :: 3.10',  # Python version
        # etc.
    ],
)
