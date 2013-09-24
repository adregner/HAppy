from setuptools import setup

setup(
    name = 'HAppy',
    version = '0.0.1',
    description = "HA resource management daemon.",
    packages = ['happy', 'happy.resources'],
    author = 'Andrew Regner',
    author_email = 'andrew.regner@mailtrust.com',
    license = 'MIT',
    url = 'https://github.com/adregner/HAppy',
    entry_points = {
        'console_scripts': [
            'happy = happy.shell:main'
            ]
        },
    package_data = {
        '/etc': [
            'conf/happy.conf'
            ]
        },
    )
