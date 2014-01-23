from os.path import dirname, join

from setuptools import setup, find_packages

def fread(fn):
    with open(join(dirname(__file__), fn), 'r') as f:
        return f.read()

setup(
    name="django-calm-cache",
    description="Django cache backend that keeps your cache calm"
    " while your site is being hammered by bucket loads of traffic",
    version="0.0.1",
    license=fread('LICENSE'),
    packages=find_packages(exclude=["tests.*", "tests"]),
    include_package_data=False,
)
