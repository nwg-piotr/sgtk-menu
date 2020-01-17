import os
from setuptools import setup


def read(f_name):
    return open(os.path.join(os.path.dirname(__file__), f_name)).read()


setup(
    name='sgtk-menu',
    version='0.5.0',
    description='GTK menu for sway and i3',
    packages=['sgtk-menu'],
    include_package_data=True,
    url='https://github.com/nwg-piotr/sgtk-menu',
    license='GPL3',
    author='Piotr Miller',
    author_email='nwg.piotr@gmail.com',
    python_requires='>=3.4.0',
    install_requires=['pygobject', 'pycairo', 'i3ipc']
)
