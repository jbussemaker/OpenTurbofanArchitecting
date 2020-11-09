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
        ],
        python_requires='>=3.6',
        packages=find_packages(),
    )
