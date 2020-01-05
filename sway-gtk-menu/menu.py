#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

"""
This is an attempt to create a menu that behaves decently on sway window manager.

Author: Piotr Miller
e-mail: nwg.piotr@gmail.com
Website: http://nwg.pl
Project: https://github.com/nwg-piotr/sway-gtk-menu
License: GPL3
"""

import os
import tempfile
import fcntl
import sys
import subprocess
import argparse

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
import cairo

try:
    from i3ipc import Connection

    i3 = Connection()
    i3ipc = True
except ModuleNotFoundError:
    i3ipc = False

# overlay window: force floating, disable border; the variable indicates if we succeeded
swaymsg: bool = subprocess.run(
    ['swaymsg', 'for_window', '[title=\"sway_gtk_menu\"]', 'floating', 'enable,', 'border', 'pixel', '0'],
    stdout=subprocess.DEVNULL).returncode == 0

c_audio_video, c_development, c_education, c_game, c_graphics, c_network, c_office, c_science, c_settings, c_system, \
c_utility, c_other = [], [], [], [], [], [], [], [], [], [], [], []

win = None
args = None


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title('sway_gtk_menu')
        self.set_role('sway_gtk_menu')
        self.connect("destroy", Gtk.main_quit)
        self.connect("button-press-event", self.die)
        self.connect('draw', self.draw)

        # Credits for transparency go to  KurtJacobson:
        # https://gist.github.com/KurtJacobson/374c8cb83aee4851d39981b9c7e2c22c
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.set_app_paintable(True)

        self.menu = None
        outer_box = Gtk.Box(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        vbox = Gtk.VBox(spacing=0, border_width=0)
        hbox = Gtk.HBox(spacing=0, border_width=0)
        self.button = Gtk.Button.new_with_label('')
        if args.right:
            hbox.pack_end(self.button, False, False, 0)
        else:
            hbox.pack_start(self.button, False, False, 0)
        if args.bottom:
            vbox.pack_end(hbox, False, False, 0)
        else:
            vbox.pack_start(hbox, False, False, 0)
        outer_box.pack_start(vbox, True, True, 0)
        self.add(outer_box)

    def resize(self, w, h):
        self.set_size_request(w, h)

    def draw(self, widget, context):
        context.set_source_rgba(0, 0, 0, args.o)
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)

    def die(self, *args):
        Gtk.main_quit()


def main():
    # exit if already running, thanks to Slava V at https://stackoverflow.com/a/384493/4040598
    pid_file = os.path.join(tempfile.gettempdir(), 'sway_gtk_menu.pid')
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        sys.exit(0)

    parser = argparse.ArgumentParser(description="A simple sway menu")
    parser.add_argument("-b", "--bottom", action="store_true", help="display at the bottom")
    parser.add_argument("-r", "--right", action="store_true", help="display on the right side")
    parser.add_argument("-s", type=int, default=20, help="menu icon size (int, min: 16, max: 48, def: 20)")
    parser.add_argument("-d", type=int, default=50, help="menu delay in milliseconds (int, def: 50)")
    parser.add_argument("-o", type=float, default=0.3, help="overlay opacity (float, min: 0.0, max: 1.0, def: 0.3)")
    global args
    args = parser.parse_args()
    if args.s < 16:
        args.s = 16
    elif args.s > 48:
        args.s = 48

    list_entries()
    global win
    win = MainWindow()
    w, h = display_dimensions()
    win.resize(w, h)
    win.menu = build_menu()
    win.show_all()
    GLib.timeout_add(args.d, open_menu)
    Gtk.main()


def open_menu():
    if not swaymsg:
        subprocess.run(['i3-msg', 'floating', 'toggle'], stdout=subprocess.DEVNULL)
        subprocess.run(['i3-msg', 'border', 'pixel', '0'], stdout=subprocess.DEVNULL)
    win.menu.popup_at_widget(win.button, Gdk.Gravity.CENTER, Gdk.Gravity.CENTER, None)


def display_dimensions():
    if i3ipc:
        root = i3.get_tree()
        found = False
        f = root.find_focused()
        while not found:
            f = f.parent
            found = f.type == 'output'
        return f.rect.width, f.rect.height
    else:
        screen = win.get_screen()
        return screen.width(), screen.height()


def list_entries():
    for f in os.listdir('/usr/share/applications'):
        _name, _exec, _icon, _categories = '', '', '', ''
        try:
            with open(os.path.join('/usr/share/applications', f)) as d:
                lines = d.readlines()
                for line in lines:
                    if line.startswith("["):
                        read_me = line.strip() == "[Desktop Entry]"
                        continue
                    if read_me:
                        if line.startswith('Name='):
                            _name = line.split('=')[1].strip()
                        if line.startswith('Exec='):
                            _exec = line.split('=')[1].strip()
                            if '%' in _exec:
                                _exec = _exec.split('%')[0].strip()
                        if line.startswith('Icon='):
                            _icon = line.split('=')[1].strip()
                        if line.startswith('Categories'):
                            _categories = line.split('=')[1].strip()

                if _name and _exec and _categories:
                    DesktopEntry(_name, _exec, _icon, _categories)

        except Exception as e:
            print(e)


class DesktopEntry(object):
    def __init__(self, name, exec, icon=None, categories=None):
        self.name = name
        self.exec = exec
        self.icon = icon
        if categories:
            self.categories = categories.split(';')[:-1]

        if self.categories:
            for category in self.categories:
                main_category = additional_to_main(category)
                if main_category == 'AudioVideo' and self not in c_audio_video:
                    c_audio_video.append(self)
                elif main_category == 'Development' and self not in c_development:
                    c_development.append(self)
                elif main_category == 'Education' and self not in c_education:
                    c_education.append(self)
                elif main_category == 'Game' and self not in c_game:
                    c_game.append(self)
                elif main_category == 'Graphics' and self not in c_graphics:
                    c_graphics.append(self)
                elif main_category == 'Network' and self not in c_network:
                    c_network.append(self)
                elif main_category == 'Office' and self not in c_office:
                    c_office.append(self)
                elif main_category == 'Science' and self not in c_science:
                    c_science.append(self)
                elif main_category == 'Settings' and self not in c_settings:
                    c_settings.append(self)
                elif main_category == 'System' and self not in c_system:
                    c_system.append(self)
                elif main_category == 'Utility' and self not in c_utility:
                    c_utility.append(self)

        if self not in c_audio_video and self not in c_development and self not in c_education \
                and self not in c_game and self not in c_graphics and self not in c_network \
                and self not in c_office and self not in c_science and self not in c_settings \
                and self not in c_system and self not in c_utility:
            c_other.append(self)

        groups = [c_audio_video, c_development, c_education, c_game, c_graphics, c_network, c_office, c_science,
                  c_settings, c_system, c_utility]

        for group in groups:
            group.sort(key=lambda x: x.name)


def build_menu():
    menu = Gtk.Menu()

    if c_audio_video:
        menu.append(sub_menu(c_audio_video, 'AudioVideo'))
    if c_development:
        menu.append(sub_menu(c_development, 'Development'))
    if c_education:
        menu.append(sub_menu(c_education, 'Education'))
    if c_game:
        menu.append(sub_menu(c_game, 'Games'))
    if c_graphics:
        menu.append(sub_menu(c_graphics, 'Graphics'))
    if c_network:
        menu.append(sub_menu(c_network, 'Network'))
    if c_office:
        menu.append(sub_menu(c_office, 'Office'))
    if c_science:
        menu.append(sub_menu(c_science, 'Science'))
    if c_settings:
        menu.append(sub_menu(c_settings, 'Settings'))
    if c_system:
        menu.append(sub_menu(c_system, 'System'))
    if c_utility:
        menu.append(sub_menu(c_utility, 'Utility'))
    if c_other:
        menu.append(sub_menu(c_other, 'Other'))

    menu.connect("hide", win.die)
    menu.show_all()

    return menu


def sub_menu(entries_list, name):
    item = Gtk.MenuItem.new_with_label(name)
    submenu = Gtk.Menu()
    submenu.set_property("reserve_toggle_size", False)
    for entry in entries_list:
        subitem = Gtk.MenuItem()
        hbox = Gtk.HBox()
        image = None
        if entry.icon:
            icon_theme = Gtk.IconTheme.get_default()
            if entry.icon.startswith('/'):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(entry.icon, args.s, args.s)
                image = Gtk.Image.new_from_pixbuf(pixbuf)
            else:
                try:
                    if entry.icon.endswith('.svg') or entry.icon.endswith('.png'):
                        entry.icon = entry.icon.split('.')[0]
                    pixbuf = icon_theme.load_icon(entry.icon, args.s, Gtk.IconLookupFlags.FORCE_SIZE)
                    image = Gtk.Image.new_from_pixbuf(pixbuf)
                except:
                    pass
        label = Gtk.Label()
        label.set_text(entry.name)
        if image:
            hbox.pack_start(image, False, False, 0)
        hbox.pack_start(label, False, False, 4)
        subitem.add(hbox)
        subitem.connect('activate', launch, entry.exec)
        submenu.append(subitem)
    item.set_submenu(submenu)

    return item


def launch(item, command):
    subprocess.Popen('exec {}'.format(command), shell=True)
    Gtk.main_quit()


def additional_to_main(category):
    """
    See https://specifications.freedesktop.org/menu-spec/latest/apas02.html
    """
    if category == 'AudioVideo' or category in ['Audio', 'Video', 'Midi', 'Mixer', 'Sequencer', 'Tuner', 'TV',
                                                'AudioVideoEditing', 'Player', 'Recorder', 'DiscBurning', 'Music']:
        return 'AudioVideo'

    elif category == 'Development' or category in ['Building', 'Debugger', 'IDE', 'GUIDesigner', 'Profiling',
                                                   'RevisionControl', 'Translation', 'WebDevelopment']:
        return 'Development'

    elif category == 'Education' or category in ['Spirituality', 'Art', 'Construction', 'Languages', 'ComputerScience',
                                                 'DataVisualization', 'ImageProcessing', 'Literature', 'Math',
                                                 'NumericalAnalysis', 'Sports', 'ParallelComputing']:
        return 'Education'

    elif category == 'Game' or category in ['ActionGame', 'AdventureGame', 'ArcadeGame', 'BoardGame', 'BlocksGame',
                                            'CardGame', 'KidsGame', 'LogicGame', 'RolePlaying', 'Shooter', 'Simulation',
                                            'SportsGame', 'StrategyGame', 'Emulator']:
        return 'Game'

    elif category == 'Graphics' or category in ['2DGraphics', 'VectorGraphics', 'RasterGraphics', '3DGraphics',
                                                'Scanning', 'OCR', 'Photography']:
        return 'Graphics'

    elif category == 'Network' or category in ['Dialup', 'InstantMessaging', 'Chat', 'IRCClient', 'Feed',
                                               'FileTransfer', 'HamRadio', 'News', 'P2P', 'RemoteAccess', 'Telephony',
                                               'VideoConference', 'WebBrowser']:
        return 'Network'

    elif category == 'Office' or category in ['Calendar', 'ContactManagement', 'Database', 'Dictionary', 'Chart',
                                              'Email', 'Finance', 'FlowChart', 'PDA', 'ProjectManagement',
                                              'Presentation', 'Spreadsheet', 'WordProcessor', 'Publishing', 'Viewer']:
        return 'Office'

    elif category == 'Science' or category in ['ArtificialIntelligence', 'Astronomy', 'Biology', 'Chemistry', 'Economy',
                                               'Electricity', 'Geography', 'Geology', 'Geoscience', 'History',
                                               'Humanities', 'MedicalSoftware', 'Physics', 'Robotics']:
        return 'Science'

    elif category == 'Settings' or category in ['DesktopSettings', 'HardwareSettings', 'PackageManager', 'Security',
                                                'Accessibility']:
        return 'Settings'

    elif category == 'System' or category in ['FileTools', 'FileManager', 'TerminalEmulator', 'Filesystem', 'Monitor']:
        return 'System'

    elif category == 'Utility' or category in ['TextTools', 'TelephonyTools', 'Maps', 'Archiving', 'Compression',
                                               'Calculator', 'Clock', 'TextEditor']:
        return 'Utility'

    else:
        return None


if __name__ == "__main__":
    main()
