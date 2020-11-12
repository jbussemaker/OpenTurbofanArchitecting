"""
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright: (c) 2020, Deutsches Zentrum fuer Luft- und Raumfahrt e.V.
Contact: jasper.bussemaker@dlr.de
"""

from open_turb_arch import __version__
from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='open_turb_arch',
        version=__version__,
        description='Open Turbofan Architecting',
        keywords='mbse mdo turbofan design architecting system',
        author='Jasper Bussemaker',
        author_email='jasper.bussemaker@dlr.de',
        classifiers=[
            'Intended Audience :: Science/Research',
            'Topic :: Scientific/Engineering',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'License :: OSI Approved :: Apache Software License',
        ],
        install_requires=[
            'pytest',
            'dataclasses',
            'pycycle @ git+https://github.com/OpenMDAO/pyCycle@3.2.0#egg=pycycle',
            'openmdao>=3.2.0',
            'ordered_set',
            'numpy',
            'Platypus-Opt',
        ],
        python_requires='>=3.6',
        packages=find_packages(),
    )
