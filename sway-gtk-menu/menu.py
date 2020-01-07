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

from tools import localized_category_names, additional_to_main, get_locale_string, config_dirs, save_default_appendix, \
    load_appendix

try:
    from i3ipc import Connection

    i3 = Connection()
    i3ipc = True
except ModuleNotFoundError:
    i3ipc = False

# Overlay window: force floating, disable border
# The variable indicates if we succeeded. If not, we'll need further command, as we're probably running i3.
# This needs further consideration: if to improve or to give on i3 support. For now it doesn't look well enough.
swaymsg: bool = subprocess.run(
    ['swaymsg', 'for_window', '[title=\"sway_gtk_menu\"]', 'floating', 'enable'],
    stdout=subprocess.DEVNULL).returncode == 0

c_audio_video, c_development, c_game, c_graphics, c_network, c_office, c_science, c_settings, c_system, \
c_utility, c_other = [], [], [], [], [], [], [], [], [], [], []

category_names = ['AudioVideo', 'Development', 'Game', 'Graphics', 'Network', 'Office', 'Science', 'Settings',
                  'System', 'Utility', 'Other']

category_icons = {"AudioVideo": "applications-multimedia",
                  "Development": "applications-development",
                  "Game": "applications-games",
                  "Graphics": "applications-graphics",
                  "Network": "applications-internet",
                  "Office": "applications-office",
                  "Science": "applications-science",
                  "Settings": "preferences-desktop",
                  "System": "preferences-system",
                  "Utility": "applications-accessories",
                  "Other": "applications-other"}

localized_names_dictionary = {}
locale = ''

win = None
args = None

config_dir = config_dirs()[0]
if not os.path.exists(config_dir):
    os.makedirs(config_dir)
appendix_file = os.path.join(config_dirs()[0], 'appendix')


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
    parser.add_argument("-a", "--append", action="store_true", help="append menu from {}".format(appendix_file))
    parser.add_argument("-l", type=str, help="force language (str, like \"en\" for English)")
    parser.add_argument("-s", type=int, default=20, help="menu icon size (int, min: 16, max: 48, def: 20)")
    parser.add_argument("-d", type=int, default=50, help="menu delay in milliseconds (int, def: 50)")
    parser.add_argument("-o", type=float, default=0.3, help="overlay opacity (float, min: 0.0, max: 1.0, def: 0.3)")
    global args
    args = parser.parse_args()
    if args.s < 16:
        args.s = 16
    elif args.s > 48:
        args.s = 48

    if not os.path.isfile(appendix_file):
        save_default_appendix(appendix_file)

    global locale
    locale = get_locale_string(args.l)
    category_names_dictionary = localized_category_names(locale)
    for name in category_names:
        main_category_name = additional_to_main(name)
        try:
            localized_names_dictionary[main_category_name] = category_names_dictionary[main_category_name]
        except:
            pass

    list_entries()
    global win
    win = MainWindow()
    w, h = display_dimensions()
    win.resize(w, h)
    win.menu = build_menu()
    win.show_all()
    GLib.timeout_add(args.d, open_menu)
    Gtk.main()


def kill_border():
    subprocess.run(['swaymsg', 'border', 'none'], stdout=subprocess.DEVNULL)


def open_menu():
    if not swaymsg:
        subprocess.run(['i3-msg', 'floating', 'toggle'], stdout=subprocess.DEVNULL)
        subprocess.run(['i3-msg', 'border', 'pixel', '0'], stdout=subprocess.DEVNULL)
    else:
        subprocess.run(['swaymsg', 'border', 'none'], stdout=subprocess.DEVNULL)

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
                        loc_name = 'Name{}='.format(locale)

                        if line.startswith('Name='):
                            _name = line.split('=')[1].strip()

                        if line.startswith(loc_name):
                            _name = line.split('=')[1].strip()

                        if line.startswith('Exec='):
                            cmd = line.split('=')[1:]
                            c = '='.join(cmd)
                            _exec = c.strip()
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
                elif main_category == 'Game' and self not in c_game:
                    c_game.append(self)
                elif main_category == 'Graphics' and self not in c_graphics:
                    c_graphics.append(self)
                elif main_category == 'Network' and self not in c_network:
                    c_network.append(self)
                elif main_category == 'Office' and self not in c_office:
                    c_office.append(self)
                elif (main_category == 'Science' or main_category == 'Education') and self not in c_science:
                    c_science.append(self)
                elif main_category == 'Settings' and self not in c_settings:
                    c_settings.append(self)
                elif main_category == 'System' and self not in c_system:
                    c_system.append(self)
                elif main_category == 'Utility' and self not in c_utility:
                    c_utility.append(self)

        if self not in c_audio_video and self not in c_development \
                and self not in c_game and self not in c_graphics and self not in c_network \
                and self not in c_office and self not in c_science and self not in c_settings \
                and self not in c_system and self not in c_utility:
            c_other.append(self)

        groups = [c_audio_video, c_development, c_game, c_graphics, c_network, c_office, c_science,
                  c_settings, c_system, c_utility]

        for group in groups:
            group.sort(key=lambda x: x.name)


def build_menu():
    menu = Gtk.Menu()

    if c_audio_video:
        append_submenu(c_audio_video, menu, 'AudioVideo')
    if c_development:
        append_submenu(c_development, menu, 'Development')
    if c_game:
        append_submenu(c_game, menu, 'Game')
    if c_graphics:
        append_submenu(c_graphics, menu, 'Graphics')
    if c_network:
        append_submenu(c_network, menu, 'Network')
    if c_office:
        append_submenu(c_office, menu, 'Office')
    if c_science:
        append_submenu(c_science, menu, 'Science')
    if c_settings:
        append_submenu(c_settings, menu, 'Settings')
    if c_system:
        append_submenu(c_system, menu, 'System')
    if c_utility:
        append_submenu(c_utility, menu, 'Utility')
    if c_other:
        append_submenu(c_other, menu, 'Other')

    if args.append:
        item = Gtk.SeparatorMenuItem()
        menu.append(item)
        appendix = load_appendix(appendix_file)
        icon_theme = Gtk.IconTheme.get_default()
        for entry in appendix:
            name = entry["name"]
            exec = entry["exec"]
            icon = entry["icon"]
            hbox = Gtk.HBox()
            label = Gtk.Label()
            label.set_text(name)
            image = None
            if icon.startswith('/'):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon, args.s, args.s)
                image = Gtk.Image.new_from_pixbuf(pixbuf)
            else:
                try:
                    if icon.endswith('.svg') or icon.endswith('.png'):
                        icon = entry.icon.split('.')[0]
                    pixbuf = icon_theme.load_icon(icon, args.s, Gtk.IconLookupFlags.FORCE_SIZE)
                    image = Gtk.Image.new_from_pixbuf(pixbuf)
                except Exception as e:
                    print(e)
            if image:
                hbox.pack_start(image, False, False, 10)
            if name:
                hbox.pack_start(label, False, False, 0)
            item = Gtk.MenuItem()
            item.add(hbox)
            item.connect('activate', launch, exec)
            menu.append(item)

    menu.connect("hide", win.die)
    menu.set_property("reserve_toggle_size", False)
    menu.show_all()

    return menu


def append_submenu(items_list, menu, submenu_name):
    try:
        menu.append(sub_menu(items_list, submenu_name, localized_names_dictionary[submenu_name]))
    except KeyError:
        menu.append(sub_menu(items_list, submenu_name, submenu_name))


def sub_menu(entries_list, name, localized_name):
    icon_theme = Gtk.IconTheme.get_default()
    outer_hbox = Gtk.HBox()
    try:
        pixbuf = icon_theme.load_icon(category_icons[name], args.s, Gtk.IconLookupFlags.FORCE_SIZE)

        image = Gtk.Image.new_from_pixbuf(pixbuf)
    except:
        image = None
    if image:
        outer_hbox.pack_start(image, False, False, 10)
    item = Gtk.MenuItem()
    main_label = Gtk.Label()
    main_label.set_text(localized_name)
    outer_hbox.pack_start(main_label, False, False, 0)
    submenu = Gtk.Menu()
    submenu.set_property("reserve_toggle_size", False)
    for entry in entries_list:
        subitem = Gtk.MenuItem()
        hbox = Gtk.HBox()
        image = None
        if entry.icon:
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
    item.add(outer_hbox)
    item.set_submenu(submenu)

    return item


def launch(item, command):
    print(command)
    subprocess.Popen('exec {}'.format(command), shell=True)
    Gtk.main_quit()


if __name__ == "__main__":
    main()
