from setuptools import setup, find_packages

setup(
    name='diff_tripleo_builds',
    version='0.0.1',
    description='Pull rpm data from logs and diff the result',
    author='Wes Hayutin',
    author_email='weshayutin@gmail.com',
    #url='https://blog.godatadriven.com/setup-py',
    packages=find_packages(include=['diff_tripleo_builds']),
    setup_requires=['pytest-runner', 'flake8'],
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
             'diff_tripleo_builds = diff_tripleo_builds.diff_builds:main',
         ]
    },

)

