#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

"""
This is an attempt to develop a menu that behaves decently on sway window manager, and also works on i3.

Author: Piotr Miller
Copyright (c) 2020 Piotr Miller & Contributors
e-mail: nwg.piotr@gmail.com
Website: http://nwg.pl
Project: https://github.com/nwg-piotr/sgtk-menu
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

from sgtk_menu.tools import (
    localized_category_names, additional_to_main, get_locale_string,
    config_dirs, load_json, save_json, create_default_configs, check_wm,
    display_geometry, data_dirs)

wm = check_wm()

# Will apply to the overlay window; we can't do so outside the config file on i3.
# We'll do it for i3 by applying commands to the focused window in open_menu method.
if wm == "sway":
    try:
        subprocess.run(['swaymsg', 'for_window', '[title=\"~sgtk-grid\"]', 'floating', 'enable'],
                       stdout=subprocess.DEVNULL).returncode == 0
    except:
        pass

other_wm = not wm == "sway" and not wm == "i3"

try:
    from pynput.mouse import Controller

    mouse_pointer = Controller()
except:
    mouse_pointer = None
    pass

geometry = (0, 0, 0, 0)

# List to hold AppButtons for favourites
all_favs = []
# Lists to hold AppBoxes for apps found in .desktop files
all_apps = []

localized_names_dictionary = {}  # name => translated name
locale = ''

win = None  # overlay window
args = None
all_items_list = []  # list of all DesktopMenuItem objects assigned to a .desktop entry
all_copies_list = []  # list of copies of above used while searching (not assigned to a submenu!)
menu_items_list = []  # created / updated with menu.get_children()
filtered_items_list = []  # used in the search method

# If we need to cheat_sway, we only add first args.t entries to all_copies list, but we need them all for searching!
missing_copies_list = []

config_dir = config_dirs()[0]
if not os.path.exists(config_dir):
    os.makedirs(config_dir)
build_from_file = os.path.join(config_dirs()[0], 'appendix')

if "XDG_CACHE_HOME" in os.environ:
    cache_dir = os.environ["XDG_CACHE_HOME"]
else:
    cache_dir = os.path.join(os.path.expanduser('~/.cache'))
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

# We track clicks in the same cache file
cache_file = os.path.join(cache_dir, 'sgtk-menu')

cache = None
sorted_cache = None


def main():
    # exit if already running, thanks to Slava V at https://stackoverflow.com/a/384493/4040598
    pid_file = os.path.join(tempfile.gettempdir(), 'sgtk-grid.pid')
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        subprocess.run("pkill -f sgtk-grid", shell=True)
        sys.exit(2)

    global build_from_file
    parser = argparse.ArgumentParser(description="GTK menu for sway, i3 and some floating WMs")
    placement = parser.add_mutually_exclusive_group()
    placement.add_argument("-b", "--bottom", action="store_true", help="display menu at the bottom (sway & i3 only)")
    placement.add_argument("-c", "--center", action="store_true", help="center menu on the screen (sway & i3 only)")

    parser.add_argument('-cn', type=int, default=6, help="number of columns to display")

    favourites = parser.add_mutually_exclusive_group()
    favourites.add_argument("-f", "--favourites", action="store_true", help="prepend 5 most used items")
    favourites.add_argument('-fn', type=int, help="prepend <FN> most used items")

    appendix = parser.add_mutually_exclusive_group()
    appendix.add_argument("-a", "--append", action="store_true",
                          help="append custom menu from {}".format(build_from_file))
    appendix.add_argument("-af", type=str, help="append custom menu from {}".format(os.path.join(config_dir, '<AF>')))

    parser.add_argument("-n", "--no-menu", action="store_true", help="skip menu, display appendix only")
    parser.add_argument("-l", type=str, help="force language (e.g. \"de\" for German)")
    parser.add_argument("-s", type=int, default=72, help="menu icon size (min: 16, max: 48, default: 20)")
    parser.add_argument("-w", type=int, help="menu width in px (integer, default: screen width / 8)")
    parser.add_argument("-d", type=int, default=100, help="menu delay in milliseconds (default: 100; sway & i3 only)")
    parser.add_argument("-o", type=float, default=0.3, help="overlay opacity (min: 0.0, max: 1.0, default: 0.3; "
                                                            "sway & i3 only)")
    parser.add_argument("-t", type=int, default=30, help="sway submenu lines limit (default: 30)")
    parser.add_argument("-y", type=int, default=30, help="y offset from edge to display menu at (sway & i3 only)")
    parser.add_argument("-css", type=str, default="grid.css",
                        help="use alternative {} style sheet instead of style.css"
                        .format(os.path.join(config_dir, '<CSS>')))
    global args
    args = parser.parse_args()

    # Create default config files if not found
    create_default_configs(config_dir)

    css_file = os.path.join(config_dirs()[0], args.css) if os.path.exists(
        os.path.join(config_dirs()[0], 'style.css')) else None

    if args.s < 16:
        args.s = 16
    elif args.s > 96:
        args.s = 96

    # We do not need any delay in other WMs
    if other_wm:
        args.d = 0

    # Replace appendix file name with custom - if any
    if args.af:
        build_from_file = os.path.join(config_dirs()[0], args.af)

    if css_file:
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider()
        try:
            provider.load_from_path(css_file)
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception as e:
            print(e)

    # cache stores number of clicks on each item
    global cache
    cache = load_json(cache_file)

    if not cache:
        save_json(cache, cache_file)
    global sorted_cache
    sorted_cache = sorted(cache.items(), reverse=True, key=lambda x: x[1])

    global locale
    locale = get_locale_string(args.l)

    screen = Gdk.Screen.get_default()
    provider = Gtk.CssProvider()
    style_context = Gtk.StyleContext()
    style_context.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # find all .desktop entries, create AppButton class instances;
    list_entries()

    # find favourites in the list above
    if args.favourites or args.fn > 0:
        list_favs()
        print("Listed {} favourites".format(len(all_favs)))

    # Overlay window
    global win
    win = MainWindow()
    if other_wm:
        # We need the window to be visible to obtain the screen geometry when i3ipc module unavailable
        win.resize(1, 1)
        win.show_all()
    global geometry
    # If we're not on sway neither i3, this won't return values until the window actually shows up.
    # Let's try as many times as needed. The retries int protects from an infinite loop.
    retries = 0
    while geometry[0] == 0 and geometry[1] == 0 and geometry[2] == 0 and geometry[3] == 0:
        geometry = display_geometry(win, wm, mouse_pointer)
        retries += 1
        if retries > 50:
            print("\nFailed to get the current screen geometry, exiting...\n")
            sys.exit(2)
    x, y, w, h = geometry

    win.resize(w, h)
    win.set_skip_taskbar_hint(True)
    win.show_all()

    # align width of all buttons
    max_width = 0
    for item in all_apps:
        width = item.get_allocated_width()
        if width > max_width:
            max_width = width
    for item in all_favs:
        item.set_size_request(max_width, max_width / 2)
    for item in all_apps:
        item.set_size_request(max_width, max_width / 2)
    win.search_box.set_size_request(max_width, 0)
    win.sep1.set_size_request(w / 2, 1)

    # GLib.timeout_add(args.d, open_menu)
    Gtk.main()


class MainWindow(Gtk.Window):
    def __init__(self):
        global args
        Gtk.Window.__init__(self)
        self.set_title('~sgtk-grid')
        self.set_role('~sgtk-grid')
        self.connect("destroy", Gtk.main_quit)
        self.connect("focus-out-event", Gtk.main_quit)
        self.connect('draw', self.draw)  # transparency
        self.screen_dimensions = (0, 0)  # parent screen dimensions (obtained outside)
        self.search_phrase = ''
        
        # Credits for transparency go to  KurtJacobson:
        # https://gist.github.com/KurtJacobson/374c8cb83aee4851d39981b9c7e2c22c
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        if other_wm:
            self.set_sensitive(False)
            self.set_resizable(False)
            self.set_decorated(False)

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        hbox = Gtk.HBox()
        self.search_box = Gtk.SearchEntry()
        self.search_box.set_property("name", "searchbox")
        self.search_box.set_text('Type to search')
        self.search_box.set_sensitive(False)
        hbox.pack_start(self.search_box, True, False, 0)
        outer_box.pack_start(hbox, False, False, args.y)

        vbox = Gtk.VBox()
        vbox.set_spacing(15)

        hbox0 = Gtk.HBox()
        print(args.cn)
        grid0 = ApplicationGrid(all_favs, columns=args.cn)
        hbox0.pack_start(grid0, True, False, 0)
        vbox.pack_start(hbox0, False, False, 0)
        
        self.sep1 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.sep1.set_property("name", "separator")
        hbox_s = Gtk.HBox()
        hbox_s.pack_start(self.sep1, True, False, 0)
        vbox.pack_start(hbox_s, True, True, 20)

        hbox1 = Gtk.HBox()
        grid = ApplicationGrid(all_apps, columns=args.cn)
        hbox1.pack_start(grid, True, False, 0)
        vbox.pack_start(hbox1, False, False, 0)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_propagate_natural_height(True)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
        scrolled_window.add(vbox)

        outer_box.pack_start(scrolled_window, True, True, 0)

        hbox = Gtk.HBox()
        self.prompt = Gtk.Label()
        self.prompt.set_text("Click")
        self.prompt.set_property("name", "prompt")
        hbox.pack_start(self.prompt, True, False, 0)
        outer_box.pack_start(hbox, False, False, args.y)
        
        self.add(outer_box)

    def search_items(self, menu, event):
        if args.no_menu:
            # we don't search custom menus
            return False

        global filtered_items_list
        if event.type == Gdk.EventType.KEY_RELEASE:
            update = False
            # search box only accepts alphanumeric characters, space and backspace
            if event.string and event.string.isalnum() or event.string == ' ':
                update = True
                # remove menu items, except for search box (item #0)
                items = self.menu.get_children()
                if len(items) > 1:
                    for item in items[1:]:
                        self.menu.remove(item)
                self.search_phrase += event.string
                self.search_box.set_text(self.search_phrase)

            elif event.keyval == 65288:  # backspace
                update = True
                self.search_phrase = self.search_phrase[:-1]
                self.search_box.set_text(self.search_phrase)

            # If our search result is a single item, we may want to activate it with the Enter key,
            # but it does not work. Here is a workaround:
            elif event.keyval == 65293 and len(filtered_items_list) == 1:
                filtered_items_list[0].activate()

            if update:
                if len(self.search_phrase) > 0:
                    filtered_items_list = []
                    for item in all_copies_list:
                        self.menu.remove(item)
                        # We'll search the entry name and the first element of its command (to skip arguments)
                        if self.search_phrase.upper() in item.name.upper() or self.search_phrase.upper() in \
                                item.exec.split()[0].upper():
                            # avoid adding twice
                            found = False
                            for i in filtered_items_list:
                                if i.name == item.name:
                                    found = True
                            if not found:
                                filtered_items_list.append(item)

                    # If we needed to cheat_sway, the values missing from all_copies_list are now here
                    if missing_copies_list:
                        for item in missing_copies_list:
                            self.menu.remove(item)
                            # We'll search the entry name and the first element of its command (to skip arguments)
                            if self.search_phrase.upper() in item.name.upper() or self.search_phrase.upper() in \
                                    item.exec.split()[0].upper():
                                # avoid adding twice
                                found = False
                                for i in filtered_items_list:
                                    if i.name == item.name:
                                        found = True
                                if not found:
                                    filtered_items_list.append(item)

                    for item in self.menu.get_children()[1:]:
                        self.menu.remove(item)

                    for item in filtered_items_list:
                        self.menu.append(item)
                        item.deselect()

                    if len(filtered_items_list) == 1:
                        item = filtered_items_list[0]
                        item.select()  # But we still can't activate with Enter

                    self.menu.show_all()
                    # as the search box is actually a menu item, it must be sensitive now,
                    # in order not to be skipped while scrolling overflowed menu
                    self.search_item.set_sensitive(True)
                    self.menu.reposition()
                else:
                    # clear search results
                    for item in self.menu.get_children():
                        self.menu.remove(item)
                    # restore original menu
                    for item in menu_items_list:
                        self.menu.append(item)
                    # better to have it insensitive when possible
                    self.search_item.set_sensitive(False)
                    self.menu.reposition()
            if len(self.search_phrase) == 0:
                self.search_box.set_text('Type to search')

        return True

    def resize(self, w, h):
        self.set_size_request(w, h)
        self.screen_dimensions = w, h

    # transparency
    def draw(self, widget, context):
        context.set_source_rgba(0, 0, 0, args.o)
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)

    def die(self, *args):
        Gtk.main_quit()


def list_entries():
    apps = []
    paths = ([os.path.join(p, 'applications') for p in data_dirs()])
    for path in paths:
        if os.path.exists(path):
            for f in os.listdir(path):
                _name, _exec, _icon, _comment = '', '', '', ''
                try:
                    with open(os.path.join(path, f)) as d:
                        lines = d.readlines()
                        read_me = True
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

                                loc_comment = 'Comment{}='.format(locale)
                                
                                if line.startswith('Comment='):
                                    _comment = line.split('=')[1].strip()

                                if line.startswith(loc_comment):
                                    _comment = line.split('=')[1].strip()

                                if line.startswith('Exec='):
                                    cmd = line.split('=')[1:]
                                    c = '='.join(cmd)
                                    _exec = c.strip()
                                    if '%' in _exec:
                                        _exec = _exec.split('%')[0].strip()
                                if line.startswith('Icon='):
                                    _icon = line.split('=')[1].strip()

                        if _name and _exec and _icon:
                            # avoid adding twice
                            found = False
                            for item in apps:
                                if item[0] == _name and item[1] == _exec:
                                    found = True
                            if not found:
                                apps.append((_name, _exec, _icon, _comment))

                except Exception as e:
                    print(e)
    apps = sorted(apps, key=lambda x: x[0].upper())
    for item in apps:
        all_apps.append(AppBox(item[0], item[1], item[2], item[3]))


def list_favs():
    # Prepend favourite items (-f or -fn argument used)
    favs_number = 0
    if args.favourites:
        favs_number = args.cn
    elif args.fn:
        favs_number = args.fn * args.cn
    if favs_number > 0:
        global sorted_cache
        if len(sorted_cache) < favs_number:
            favs_number = len(sorted_cache)

        to_prepend = []
        for i in range(favs_number):
            fav_exec = sorted_cache[i][0]
            for button in all_apps:
                if button.exec == fav_exec and button not in to_prepend:
                    to_prepend.append(button)
                    break  # stop searching, there may be duplicates on the list
        for button in to_prepend:
            all_favs.append(AppBox(button.name, button.exec, button.icon, button.comment))


class AppBox(Gtk.EventBox):
    def __init__(self, name, _exec, icon, comment):
        super().__init__()
        self.name = name
        self.exec = _exec
        self.icon = icon
        self.comment = comment
        if len(name) > 25:
            name = "{}...".format(name[:22])
        box = Gtk.Box()
        box.set_property("name", "button")

        self.connect("enter-notify-event", on_button_focused)
        
        button = Gtk.Button()
        button.set_property("name", "button")
        button.set_always_show_image(True)
        button.set_image(app_image(icon))
        button.set_image_position(Gtk.PositionType.TOP)
        button.set_label(name)
        button.connect("clicked", launch, _exec)
        self.connect("focus", on_button_focused)
        self.connect("proximity-in-event", on_button_focused)
        box.pack_start(button, True, True, 5)
        self.add(box)


def app_image(icon):
    """
    Creates a Gtk.Image instance
    :param icon: sys icon name or .svg / png path
    :return: Gtk.Image
    """
    image = None
    icon_theme = Gtk.IconTheme.get_default()
    if icon.startswith('/'):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon, args.s, args.s)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
        except:
            pass
    else:
        try:
            if icon.endswith('.svg') or icon.endswith('.png'):
                icon = icon.split('.')[0]
            pixbuf = icon_theme.load_icon(icon, args.s, Gtk.IconLookupFlags.FORCE_SIZE)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
        except:
            pass
    return image


class ApplicationGrid(Gtk.Grid):
    def __init__(self, items_list, columns=6):
        super().__init__()
        self.set_column_spacing(25)
        self.set_row_spacing(15)
        col, row = 0, 0
        for item in items_list:
            if not item.get_parent():  # check if not yet attached (e.g. in favourites)
                self.attach(item, col, row, 1, 1)
                if col < columns - 1:
                    col += 1
                else:
                    col = 0
                    row += 1


def on_button_focused(button, event):
    if button.comment:
        win.prompt.set_text(button.comment)
    else:
        win.prompt.set_text(button.name)


def launch(item, command, no_cache=False):
    if not no_cache:
        # save command and increased clicks counter to the cache file; we won't cache items from the user-defined menu
        if command not in cache:
            cache[command] = 1
        else:
            cache[command] += 1
        save_json(cache, cache_file)
    # run the command an quit
    subprocess.Popen('exec {}'.format(command), shell=True)
    Gtk.main_quit()


if __name__ == "__main__":
    main()
