import os
from setuptools import setup


def read(f_name):
    return open(os.path.join(os.path.dirname(__file__), f_name)).read()


setup(
    name='sway-gtk-menu',
    version='0.0.1',
    description='GTK+ menu for sway window manager',
    packages=['sway-gtk-menu'],
    include_package_data=True,
    url='https://github.com/nwg-piotr/sway-gtk-menu',
    license='GPL3',
    author='Piotr Miller',
    author_email='nwg.piotr@gmail.com',
    python_requires='>=3.4.0',
    install_requires=['pygobject', 'i3ipc']
)
