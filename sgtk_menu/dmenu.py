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

from sgtk_menu.tools import (config_dirs, load_json, create_default_configs, check_wm, display_geometry, path_dirs)

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

try:
    from pynput.mouse import Controller

    mouse_pointer = Controller()
except:
    mouse_pointer = None
    pass

geometry = (0, 0, 0, 0)

win = None  # overlay window
args = None
all_items_list = []  # list of all DesktopMenuItem objects assigned to a .desktop entry
all_copies_list = []  # list of copies of above used while searching (not assigned to a submenu!)
menu_items_list = []  # created / updated with menu.get_children()
filtered_items_list = []  # used in the search method

all_commands_list = []

config_dir = config_dirs()[0]
if not os.path.exists(config_dir):
    os.makedirs(config_dir)
build_from_file = os.path.join(config_dirs()[0], 'appendix')


def main():
    # exit if already running, thanks to Slava V at https://stackoverflow.com/a/384493/4040598
    pid_file = os.path.join(tempfile.gettempdir(), 'sgtk-dmenu.pid')
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        subprocess.run("pkill -f sgtk-dmenu", shell=True)
        sys.exit(2)

    global build_from_file
    parser = argparse.ArgumentParser(description="GTK menu for sway, i3 and some floating WMs")
    placement = parser.add_mutually_exclusive_group()
    placement.add_argument("-b", "--bottom", action="store_true", help="display menu at the bottom (sway & i3 only)")
    placement.add_argument("-c", "--center", action="store_true", help="center menu on the screen (sway & i3 only)")

    appendix = parser.add_mutually_exclusive_group()
    appendix.add_argument("-a", "--append", action="store_true",
                          help="append custom menu from {}".format(build_from_file))
    appendix.add_argument("-af", type=str, help="append custom menu from {}".format(os.path.join(config_dir, '<AF>')))

    parser.add_argument("-s", type=int, default=20, help="menu icon size (min: 16, max: 48, default: 20)")
    parser.add_argument("-w", type=int, help="menu width in px (integer, default: screen width / 8)")
    parser.add_argument("-d", type=int, default=100, help="menu delay in milliseconds (default: 100; sway & i3 only)")
    parser.add_argument("-o", type=float, default=0.3, help="overlay opacity (min: 0.0, max: 1.0, default: 0.3; "
                                                            "sway & i3 only)")
    parser.add_argument("-t", type=int, default=15, help="lines limit (default: 20)")
    parser.add_argument("-y", type=int, default=0, help="y offset from edge to display menu at (sway & i3 only)")
    parser.add_argument("-css", type=str, default="style.css",
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
    elif args.s > 48:
        args.s = 48

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

    screen = Gdk.Screen.get_default()
    provider = Gtk.CssProvider()
    style_context = Gtk.StyleContext()
    style_context.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # find all .desktop entries, create DesktopEntry class instances;
    # DesktopEntry adds itself to the proper List in the class constructor
    global all_commands_list
    all_commands_list = list_commands()
    print(len(all_commands_list))
    all_commands_list = sorted(all_commands_list)

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
        geometry = display_geometry(win, wm, mouse_pointer)
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
    win.menu = build_menu(all_commands_list)
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
        global filtered_items_list
        if event.type == Gdk.EventType.KEY_RELEASE:
            update = False
            # search box only accepts alphanumeric characters, space and backspace
            if event.string and event.string.isalnum() or event.string in [' ', '-', '+', '_']:
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
                        label = item.get_label()
                        if self.search_phrase.upper() in label.upper():
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


def list_commands():
    commands = []
    for path in path_dirs():
        if os.path.exists(path):
            for command in os.listdir(path):
                if not "." in command:
                    commands.append(command)
    return commands


def build_menu(commands):
    icon_theme = Gtk.IconTheme.get_default()
    menu = Gtk.Menu()

    win.search_item = Gtk.MenuItem()
    win.search_item.add(win.search_box)
    win.search_item.set_sensitive(False)
    menu.add(win.search_item)

    # actual drun menu
    for command in commands:
        item = Gtk.MenuItem.new_with_label(command)
        item.set_property("name", "item-drun")
        item.connect('activate', launch, command)
        all_items_list.append(item)
        all_copies_list.append(item)

    for item in all_items_list[:args.t]:
        menu.append(item)

    # user-defined menu from default or custom file (see args)
    if args.append or args.af:
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


def launch(item, command, terminal=False):
    # run the command an quit
    subprocess.Popen('exec {}'.format(command), shell=True)
    Gtk.main_quit()


if __name__ == "__main__":
    main()
