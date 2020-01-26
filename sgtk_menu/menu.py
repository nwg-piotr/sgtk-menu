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
    display_geometry)

wm = check_wm()

# Will apply to the overlay window; we can't do so outside the config file on i3.
# We'll do it for i3 by applying commands to the focused window in open_menu method.
if wm == "sway":
    try:
        subprocess.run(['swaymsg', 'for_window', '[title=\"~sgtk-menu\"]', 'floating', 'enable'],
                       stdout=subprocess.DEVNULL).returncode == 0
    except:
        pass

other_wm = not wm == "sway" and not wm == "i3"

if not other_wm:
    from i3ipc import Connection
    i3 = Connection()
else:
    i3 = None

try:
    from pynput.mouse import Controller

    mouse_pointer = Controller()
except:
    mouse_pointer = None
    pass

geometry = (0, 0, 0, 0)

# Lists to hold DesktopEntry objects of each category
c_audio_video, c_development, c_game, c_graphics, c_network, c_office, c_science, c_settings, c_system, \
c_utility, c_other, all_entries = [], [], [], [], [], [], [], [], [], [], [], []

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
cache_file = os.path.join(cache_dir, 'sgtk-menu')

cache = None
sorted_cache = None


def main():
    # exit if already running, thanks to Slava V at https://stackoverflow.com/a/384493/4040598
    pid_file = os.path.join(tempfile.gettempdir(), 'sgtk-menu.pid')
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        subprocess.run("pkill -f sgtk-menu", shell=True)
        sys.exit(2)

    global build_from_file
    parser = argparse.ArgumentParser(description="GTK menu for sway, i3 and some floating WMs")
    placement = parser.add_mutually_exclusive_group()
    placement.add_argument("-b", "--bottom", action="store_true", help="display menu at the bottom (sway & i3 only)")
    placement.add_argument("-c", "--center", action="store_true", help="center menu on the screen (sway & i3 only)")

    favourites = parser.add_mutually_exclusive_group()
    favourites.add_argument("-f", "--favourites", action="store_true", help="prepend 5 most used items")
    favourites.add_argument('-fn', type=int, help="prepend <FN> most used items")

    appendix = parser.add_mutually_exclusive_group()
    appendix.add_argument("-a", "--append", action="store_true",
                          help="append custom menu from {}".format(build_from_file))
    appendix.add_argument("-af", type=str, help="append custom menu from {}".format(os.path.join(config_dir, '<AF>')))

    parser.add_argument("-n", "--no-menu", action="store_true", help="skip menu, display appendix only")
    parser.add_argument("-l", type=str, help="force language (e.g. \"de\" for German)")
    parser.add_argument("-s", type=int, default=20, help="menu icon size (min: 16, max: 48, default: 20)")
    parser.add_argument("-w", type=int, help="menu width in px (integer, default: screen width / 8)")
    parser.add_argument("-d", type=int, default=100, help="menu delay in milliseconds (default: 100; sway & i3 only)")
    parser.add_argument("-o", type=float, default=0.3, help="overlay opacity (min: 0.0, max: 1.0, default: 0.3; "
                                                            "sway & i3 only)")
    parser.add_argument("-t", type=int, default=30, help="sway submenu lines limit (default: 30)")
    parser.add_argument("-y", type=int, default=0, help="y offset from edge to display menu at (sway & i3 only)")
    parser.add_argument("-css", type=str, default="style.css",
                        help="use alternative {} style sheet instead of style.css"
                        .format(os.path.join(config_dir, '<CSS>')))
    global args
    args = parser.parse_args()
    css_file = os.path.join(config_dirs()[0], args.css) if os.path.exists(
        os.path.join(config_dirs()[0], 'style.css')) else None

    if args.s < 16:
        args.s = 16
    elif args.s > 48:
        args.s = 48

    # We do not need any delay in other WMs
    if other_wm:
        args.d = 0

    # Create default config files if not found
    create_default_configs(config_dir)

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
    category_names_dictionary = localized_category_names(locale)

    # replace additional category names with main ones
    for name in category_names:
        main_category_name = additional_to_main(name)
        try:
            localized_names_dictionary[main_category_name] = category_names_dictionary[main_category_name]
        except:
            pass

    screen = Gdk.Screen.get_default()
    provider = Gtk.CssProvider()
    style_context = Gtk.StyleContext()
    style_context.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # find all .desktop entries, create DesktopEntry class instances;
    # DesktopEntry adds itself to the proper List in the class constructor
    list_entries()

    # Overlay window
    global win
    win = MainWindow()
    if other_wm:
        # We need this to obtain the screen geometry when i3ipc module unavailable
        win.resize(1, 1)
        win.show_all()
    global geometry
    # If we're not on sway neither i3, this won't return values until the window actually shows up.
    # Let's try as many times as needed. The retries int protects from an infinite loop.
    retries = 0
    while geometry[0] == 0 and geometry[1] == 0 and geometry[2] == 0 and geometry[3] == 0:
        geometry = display_geometry(win, i3, mouse_pointer)
        retries += 1
        if retries > 50:
            print("\nFailed to get the current screen geometry, exiting...\n")
            sys.exit(2)
    x, y, w, h = geometry

    if not other_wm:
        win.resize(w, h)
    else:
        win.resize(1, 1)
        win.set_gravity(Gdk.Gravity.CENTER)
        if mouse_pointer:
            x, y = mouse_pointer.position
            win.move(x, y)
        else:
            win.move(0, 0)
            print("\nYou need the python-pynput package!\n")

    win.set_skip_taskbar_hint(True)
    win.menu = build_menu()
    win.menu.set_property("name", "menu")

    global menu_items_list
    menu_items_list = win.menu.get_children()

    win.menu.propagate_key_event = False
    win.menu.connect("key-release-event", win.search_items)
    # Let's reserve some width for long entries found with the search box
    if args.w:
        win.menu.set_property("width_request", args.w)
    else:
        win.menu.set_property("width_request", int(win.screen_dimensions[0] / 8))
    win.show_all()

    GLib.timeout_add(args.d, open_menu)
    Gtk.main()


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title('~sgtk-menu')
        self.set_role('~sgtk-menu')
        self.connect("destroy", Gtk.main_quit)
        self.connect('draw', self.draw)  # transparency

        if other_wm:
            self.set_sensitive(False)
            self.set_resizable(False)
            self.set_decorated(False)

        self.search_box = Gtk.SearchEntry()
        self.search_box.set_property("name", "searchbox")
        self.search_box.set_text('Type to search')
        self.screen_dimensions = (0, 0)  # parent screen dimensions (obtained outside)
        self.search_phrase = ''

        # Credits for transparency go to  KurtJacobson:
        # https://gist.github.com/KurtJacobson/374c8cb83aee4851d39981b9c7e2c22c
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        self.menu = None  # We'll create it outside the class

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox = Gtk.VBox()
        hbox = Gtk.HBox()

        # the widget we'll popup menu at
        self.anchor = Gtk.Box()
        if args.center:
            hbox.pack_start(self.anchor, True, True, 0)
        else:
            hbox.pack_start(self.anchor, False, False, 0)

        if args.bottom:
            # display menu at the bottom
            vbox.pack_end(hbox, False, False, 0)
        else:
            if args.center:
                # center on the screen
                vbox.pack_start(hbox, True, True, 0)
            else:
                # display on top
                vbox.pack_start(hbox, False, False, 0)
        outer_box.pack_start(vbox, True, True, args.y)

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


def open_menu():
    if wm == "sway":
        subprocess.run(['swaymsg', 'border', 'none'], stdout=subprocess.DEVNULL)
    elif wm == "i3":
        # we couldn't do this on i3 at the script start
        subprocess.run(['i3-msg', 'floating', 'enable'], stdout=subprocess.DEVNULL)
        subprocess.run(['i3-msg', 'border', 'none'], stdout=subprocess.DEVNULL)

    if args.bottom:
        gravity = Gdk.Gravity.SOUTH
    elif args.center:
        gravity = Gdk.Gravity.CENTER
    else:
        gravity = Gdk.Gravity.NORTH

    if not other_wm:
        win.menu.popup_at_widget(win.anchor, gravity, gravity, None)
    else:
        win.menu.popup_at_widget(win.anchor, Gdk.Gravity.CENTER, Gdk.Gravity.CENTER, None)
        if not win.menu.get_visible():
            # In Openbox, if the MainWindow (which is invisible!) gets accidentally clicked and dragged,
            # the menu doesn't pop up, but the process is still alive. Let's kill the bastard, if so.
            Gtk.main_quit()


def list_entries():
    paths = [os.path.expanduser('~/.local/share/applications'), "/usr/share/applications",
             "/usr/local/share/applications"]
    for path in paths:
        if os.path.exists(path):
            for f in os.listdir(path):
                _name, _exec, _icon, _categories = '', '', '', ''
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
                            # this will hold the data we need, and also automagically append itself to the proper list
                            entry = DesktopEntry(_name, _exec, _icon, _categories)
                            # we need this list for the favourites menu
                            all_entries.append(entry)
                except Exception as e:
                    print(e)


class DesktopEntry(object):
    """
    Should be self-explanatory
    """

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
    icon_theme = Gtk.IconTheme.get_default()
    menu = Gtk.Menu()

    if not args.no_menu:
        win.search_item = Gtk.MenuItem()
        win.search_item.add(win.search_box)
        win.search_item.set_sensitive(False)
        menu.add(win.search_item)

        # Prepend favourite items (-f or -fn argument used)
        favs_number = 0
        if args.favourites:
            favs_number = 5
        elif args.fn:
            favs_number = args.fn
        if favs_number > 0:
            global sorted_cache
            if len(sorted_cache) < favs_number:
                favs_number = len(sorted_cache)

            to_prepend = []  # list of favourite items
            for i in range(favs_number):
                fav_exec = sorted_cache[i][0]
                for item in all_entries:
                    if item.exec == fav_exec and item not in to_prepend:
                        to_prepend.append(item)
                        break  # stop searching, there may be duplicates on the list

            # build menu items
            for entry in to_prepend:
                name = entry.name
                exec = entry.exec
                icon = entry.icon
                hbox = Gtk.HBox()
                label = Gtk.Label()
                label.set_text(name)
                image = None
                if icon.startswith('/'):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon, args.s, args.s)
                        image = Gtk.Image.new_from_pixbuf(pixbuf)
                    except:
                        pass
                else:
                    try:
                        if icon.endswith('.svg') or icon.endswith('.png'):
                            icon = entry.icon.split('.')[0]
                        pixbuf = icon_theme.load_icon(icon, args.s, Gtk.IconLookupFlags.FORCE_SIZE)
                        image = Gtk.Image.new_from_pixbuf(pixbuf)
                    except:
                        pass
                if image:
                    hbox.pack_start(image, False, False, 10)
                if name:
                    hbox.pack_start(label, False, False, 0)
                item = Gtk.MenuItem()
                item.set_property("name", "item")
                item.add(hbox)
                item.connect('activate', launch, exec)
                menu.append(item)

            if to_prepend:
                separator = Gtk.SeparatorMenuItem()
                separator.set_property("name", "separator")
                menu.append(separator)

        # actual system menu with submenus for each category
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

    # user-defined menu from default or custom file (see args)
    if args.append or args.af or args.no_menu:
        if not args.no_menu:  # nothing above to separate
            separator = Gtk.SeparatorMenuItem()
            separator.set_property("name", "separator")
            menu.append(separator)
        appendix = load_json(build_from_file)
        for entry in appendix:
            name = entry["name"]
            exec = entry["exec"]
            icon = entry["icon"]
            hbox = Gtk.HBox()
            label = Gtk.Label()
            label.set_text(name)
            image = None
            if icon.startswith('/'):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon, args.s, args.s)
                    image = Gtk.Image.new_from_pixbuf(pixbuf)
                except:
                    pass
            else:
                try:
                    if icon.endswith('.svg') or icon.endswith('.png'):
                        icon = entry.icon.split('.')[0]
                    pixbuf = icon_theme.load_icon(icon, args.s, Gtk.IconLookupFlags.FORCE_SIZE)
                    image = Gtk.Image.new_from_pixbuf(pixbuf)
                except:
                    pass
            if image:
                hbox.pack_start(image, False, False, 10)
            if name:
                hbox.pack_start(label, False, False, 0)
            item = Gtk.MenuItem()
            item.set_property("name", "item")
            item.add(hbox)
            item.connect('activate', launch, exec, True)  # do not cache!
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


class SubMenu(Gtk.Menu):
    """
    We need to subclass Gtk.Menu, to assign its .desktop entries list to it.
    Needed to workaround the sway overflowing menus issue. See cheat_sway and cheat_sway_on_exit methods.
    """

    def __init__(self):
        Gtk.Menu.__init__(self)
        self.entries_list = list


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
    item.set_property("name", "item")
    item.entries_list = entries_list
    main_label = Gtk.Label()
    main_label.set_text(localized_name)
    outer_hbox.pack_start(main_label, False, False, 0)

    submenu = SubMenu()
    submenu.set_property("name", "submenu")
    submenu.entries_list = entries_list

    submenu.set_property("reserve_toggle_size", False)
    # On sway 1.2, if popped-up menu length exceeds the screen height, no buttons to scroll appear,
    # and the mouse scroller does not work, too. We need a workaround!
    if not wm == "sway" or len(entries_list) < args.t:  # -t stands for sway submenu lines limit
        # We are not on sway or submenu is short enough
        for entry in entries_list:
            subitem = DesktopMenuItem(icon_theme, entry.name, entry.exec, entry.icon)
            subitem.connect('activate', launch, entry.exec)
            all_items_list.append(subitem)

            subitem_copy = DesktopMenuItem(icon_theme, entry.name, entry.exec, entry.icon)
            subitem_copy.connect('activate', launch, entry.exec)
            subitem_copy.show()
            all_copies_list.append(subitem_copy)

            submenu.append(subitem)

        item.add(outer_hbox)
        submenu.connect("key-release-event", win.search_items)
        item.set_submenu(submenu)
    else:
        # This will be tricky as hell. We only add args.t items here.
        # The rest must be added on menu popped-up (cheat_sway).
        for i in range(args.t):
            entry = entries_list[i]
            subitem = DesktopMenuItem(icon_theme, entry.name, entry.exec, entry.icon)
            subitem.connect('activate', launch, entry.exec)
            all_items_list.append(subitem)

            subitem_copy = DesktopMenuItem(icon_theme, entry.name, entry.exec, entry.icon)
            subitem_copy.connect('activate', launch, entry.exec)
            subitem_copy.show()
            all_copies_list.append(subitem_copy)

            submenu.append(subitem)

        # If we're cheating sway, entries above args.t will be missing from all_copies_list.
        # Let's store them here for searching purposes.
        for entry in entries_list[args.t:]:
            subitem_copy = DesktopMenuItem(icon_theme, entry.name, entry.exec, entry.icon)
            subitem_copy.connect('activate', launch, entry.exec)
            subitem_copy.show()
            missing_copies_list.append(subitem_copy)

        item.add(outer_hbox)
        submenu.connect("key-release-event", win.search_items)
        submenu.connect("popped-up", cheat_sway, submenu.entries_list)
        submenu.connect("hide", cheat_sway_on_exit)
        item.set_submenu(submenu)

    return item


def cheat_sway(menu, flipped_rect, final_rect, flipped_x, flipped_y, entries_list):
    """
    If we're on sway, all submenus items number have been limited to args.t during their creation, to workaround
    sway 1.2 / GTK bug. This method is being called on submenu popped-up, to add missing items. We'll have to remove
    them on submenu exit event (cheat_sway_on_exit). But scrolling overflowed menus works on sway, hurray!
    """
    if len(menu.get_children()) < len(entries_list):
        icon_theme = Gtk.IconTheme.get_default()
        for i in range(args.t, len(entries_list)):
            entry = entries_list[i]
            subitem = DesktopMenuItem(icon_theme, entry.name, entry.exec, entry.icon)
            subitem.connect('activate', launch, entry.exec)

            found = False
            for it in all_items_list:
                if it.name == subitem.name:
                    found = True
            if not found:
                all_items_list.append(subitem)

            subitem_copy = DesktopMenuItem(icon_theme, entry.name, entry.exec, entry.icon)
            subitem_copy.connect('activate', launch, entry.exec)
            subitem_copy.show()

            found = False
            for it in all_copies_list:
                if it.name == subitem.name:
                    found = True
            if not found:
                all_copies_list.append(subitem_copy)

            menu.append(subitem)
    menu.show_all()
    menu.reposition()


def cheat_sway_on_exit(submenu):
    for item in submenu.get_children()[args.t:]:
        submenu.remove(item)


class DesktopMenuItem(Gtk.MenuItem):
    """
    We'll a Gtk.MenuItem here, w/ a hbox inside; the box contains an icon and a label.
    """

    def __init__(self, icon_theme, name, _exec, icon_name=None):
        Gtk.MenuItem.__init__(self)
        self.name = name
        self.set_property("name", "item")
        self.exec = _exec
        hbox = Gtk.HBox()
        image = None
        if icon_name:
            if icon_name.startswith('/'):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, args.s, args.s)
                    image = Gtk.Image.new_from_pixbuf(pixbuf)
                except:
                    pass
            else:
                try:
                    if icon_name.endswith('.svg') or icon_name.endswith('.png'):
                        icon_name = icon_name.split('.')[0]
                    pixbuf = icon_theme.load_icon(icon_name, args.s, Gtk.IconLookupFlags.FORCE_SIZE)
                    image = Gtk.Image.new_from_pixbuf(pixbuf)
                except:
                    pass
        self.icon = image
        label = Gtk.Label()
        label.set_text(self.name)
        if image:
            hbox.pack_start(image, False, False, 0)
        hbox.pack_start(label, False, False, 4)
        self.add(hbox)


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
