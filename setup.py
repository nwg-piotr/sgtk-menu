import os
from setuptools import setup, find_packages


def read(f_name):
    return open(os.path.join(os.path.dirname(__file__), f_name)).read()


setup(
    name='sgtk-menu',
    version='1.2.1',
    description='GTK menu for sway, i3 and some other WMs',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["config/*"]
    },
    url='https://github.com/nwg-piotr/sgtk-menu',
    license='GPL3',
    author='Piotr Miller',
    author_email='nwg.piotr@gmail.com',
    python_requires='>=3.4.0',
    install_requires=['pygobject', 'pycairo'],
    entry_points={
        'gui_scripts': [
            'sgtk-menu = sgtk_menu.menu:main',
            'sgtk-bar = sgtk_menu.bar:main',
            'sgtk-dmenu = sgtk_menu.dmenu:main',
            'sgtk-grid = sgtk_menu.grid:main',
        ]
    },
)
