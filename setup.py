# -*- coding: utf-8 -*-

import os

from setuptools import find_packages
from setuptools import setup

# manage package version
package_version = '0.1.0'


# get readme and changes
here = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(here, 'README.txt')) as text_file:
        README = text_file.read()
    with open(os.path.join(here, 'CHANGES.txt')) as text_file:
        CHANGES = text_file.read()
except IOError:
    README = CHANGES = ''

# set up requires
install_requires = ['rethinkdb>=2.3.0', 'pyramid>=1.3']
testing_requires = ['nose']
testing_extras = testing_requires + ['coverage']
docs_extras = ['sphinx']


def main():

    setup(
        name='pyramid_rethinkdb_sessions',
        version=package_version,
        description='Pyramid web framework session factory backed by rethinkdb',
        long_description=README + '\n\n' + CHANGES,
        classifiers=[
            'Intended Audience :: Developers',
            "Framework :: Pyramid",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3.3",
            "Programming Language :: Python :: 3.4",
            ],
        keywords='pyramid session rethinkdb',
        author='Nanang Suryadi',
        author_email='nanang.suryadi@boolein.com',
        url='https://github.com/suryakencana/pyramid_rethinkdb_sessions',
        license='FreeBSD',
        packages=find_packages(),
        #test_suite='pyramid_rethinkdb_sessions.tests',
        test_suite='nose.collector',
        include_package_data=True,
        zip_safe=False,
        tests_require=testing_requires,
        install_requires=install_requires,
        entry_points='',
        extras_require={
            'testing': testing_extras,
            'docs': docs_extras,
            },
    )

if __name__ == '__main__':
    main()
