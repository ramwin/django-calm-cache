import sys
from os.path import dirname, join

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCmd


class ToxCmd(TestCmd, object):
    def finalize_options(self):
        super(ToxCmd, self).finalize_options()
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import tox
        sys.exit(tox.cmdline(self.test_args))


def fread(fn):
    with open(join(dirname(__file__), fn), 'r') as f:
        return f.read()

setup(
    name="django3-calm-cache",
    description="A set of useful tools that enhance the standard Django cache experience",
    long_description=fread('README.md'),
    long_description_content_type="text/markdown",
    keywords="django cache memcache memcached minting pylibmc libmemcached",
    author="Xiang Wang",
    author_email="ramwin@qq.com",
    url="https://github.com/ramwin/django-calm-cache",
    version="1.0.1",
    license="BSD 3-Clause",
    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
    ],
    platforms=['Platform Independent',],
    packages=find_packages(exclude=["tests.*", "tests"]),
    include_package_data=False,
    tests_require=['tox'],
    cmdclass={'test': ToxCmd},
)
