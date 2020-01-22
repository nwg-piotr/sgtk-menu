#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

"""
This is an external command for the sgtk-menu package to display a button bar w/ user-defined commands.

Author: Piotr Miller
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

from tools import config_dirs, load_json, create_default_configs

# Will apply to the overlay window; we can't do so outside the config file on i3.
# We'll do it for i3 by applying commands to the focused window in open_menu method.
# The variable indicates if we succeeded / are on sway.
swaymsg = False
try:
    swaymsg = subprocess.run(
        ['swaymsg', 'for_window', '[title=\"~sgtk-bar\"]', 'floating', 'enable'],
        stdout=subprocess.DEVNULL).returncode == 0
except:
    pass

i3_msg = False
try:
    i3_msg = subprocess.run(
        ['i3-msg', '-t', 'get_outputs'],
        stdout=subprocess.DEVNULL).returncode == 0
except:
    pass
other_wm = not swaymsg and not i3_msg

if not other_wm:
    from i3ipc import Connection

    i3 = Connection()

geometry = (0, 0, 0, 0)

win = None  # overlay window
args = None


config_dir = config_dirs()[0]
if not os.path.exists(config_dir):
    os.makedirs(config_dir)
build_from_file = os.path.join(config_dirs()[0], 'exit')


def main():
    # exit if already running, thanks to Slava V at https://stackoverflow.com/a/384493/4040598
    pid_file = os.path.join(tempfile.gettempdir(), 'sgtk-bar.pid')
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        subprocess.run("pkill -f sgtk-bar", shell=True)
        sys.exit(2)

    global build_from_file

    parser = argparse.ArgumentParser(description="Button bar for sgtk-menu")
    placement = parser.add_mutually_exclusive_group()

    parser.add_argument("-bf", type=str, help="build from file (default: {})".format(build_from_file))
    parser.add_argument("-bw", type=int, default=90, help="minimum button width (default: 90)")
    parser.add_argument("-bh", type=int, default=90, help="minimum button height (default: 90)")
    placement.add_argument("-b", "--bottom", action="store_true", help="display bar at the bottom")
    placement.add_argument("-t", "--top", action="store_true", help="display bar at the top")
    parser.add_argument("-x", type=int, default=0, help="horizontal offset from edge")
    parser.add_argument("-y", type=int, default=0, help="vertical offset from edge")
    parser.add_argument("-v", "--vertical", action="store_true", help="arrange buttons vertically")
    parser.add_argument("-p", type=int, default=20, help="button padding (default: 20)")
    parser.add_argument("-s", type=int, default=32, help="icon size (min: 16, max: 48, default: 32)")
    parser.add_argument("-d", type=int, default=100, help="bar delay in milliseconds (default: 100; sway & i3 only)")
    parser.add_argument("-o", type=float, default=0.3, help="overlay opacity (min: 0.0, max: 1.0, default: 0.3)")

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
    if args.bf:
        build_from_file = os.path.join(config_dirs()[0], args.bf)

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

    # Overlay window
    global win
    win = MainWindow()
    global geometry
    # If we're not on sway neither i3, this won't return values until the window actually shows up.
    # Let's try as many times as needed. The retries int protects from an infinite loop.
    retries = 0
    while geometry[0] == 0 and geometry[1] == 0 and geometry[2] == 0 and geometry[3] == 0:
        geometry = display_geometry()
        retries += 1
        if retries > 500:
            print("\nFailed to get the current screen geometry, exiting...\n")
            sys.exit(2)
    x, y, w, h = geometry

    win.resize(w, h)
    win.set_gravity(Gdk.Gravity.CENTER)

    win.button_bar.set_property("name", "button")

    win.show()
    #win.set_skip_taskbar_hint(True)
    GLib.timeout_add(args.d, show_bar)
    Gtk.main()


class MainWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title('~sgtk-bar')
        self.set_role('~sgtk-bar')
        self.connect("destroy", Gtk.main_quit)
        self.connect('draw', self.draw)  # transparency
        self.connect("key-release-event", self.key_pressed)
        self.connect("button-press-event", Gtk.main_quit)

        if other_wm:
            self.set_resizable(False)
            self.set_decorated(False)
            self.set_modal(True)

        # Credits for transparency go to  KurtJacobson:
        # https://gist.github.com/KurtJacobson/374c8cb83aee4851d39981b9c7e2c22c
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        if args.vertical:
            self.anchor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        else:
            self.anchor = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.button_bar = build_bar()
        self.anchor.pack_start(self.button_bar, False, False, 0)

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox = Gtk.VBox()
        hbox = Gtk.HBox()

        if not args.top and not args.bottom:
            hbox.pack_start(self.anchor, True, False, args.x)
        else:
            hbox.pack_start(self.anchor, False, False, args.x)

        if args.bottom:
            # display menu at the bottom
            vbox.pack_end(hbox, False, False, 0)
        else:
            if args.top:
                # display on top
                vbox.pack_start(hbox, False, False, 0)
            else:
                # center on the screen
                vbox.pack_start(hbox, True, False, 0)
        outer_box.pack_start(vbox, True, True, args.y)

        self.add(outer_box)

    def resize(self, w, h):
        self.set_size_request(w, h)

    # transparency
    def draw(self, widget, context):
        context.set_source_rgba(0, 0, 0, args.o)
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)

    def key_pressed(self, window, event):
        if event.type == Gdk.EventType.KEY_RELEASE:
            print(event.keyval)
            # Escape
            if event.keyval == 65307:
                Gtk.main_quit()


def show_bar():
    if not swaymsg:
        if not other_wm:
            # we couldn't do this on i3 at the script start
            subprocess.run(['i3-msg', 'floating', 'enable'], stdout=subprocess.DEVNULL)
            subprocess.run(['i3-msg', 'border', 'none'], stdout=subprocess.DEVNULL)
    else:
        if not other_wm:
            subprocess.run(['swaymsg', 'border', 'none'], stdout=subprocess.DEVNULL)
            
    win.show_all()


def display_geometry():
    """
    Obtain geometry of currently focused display
    :return: (x, y, width, height)
    """
    if not other_wm:
        # On sway or i3 we use i3ipc, to avoid less reliable, Gdk-based way.
        # We should get results at 1st try.
        root = i3.get_tree()
        found = False
        f = root.find_focused()
        while not found:
            f = f.parent
            found = f.type == 'output'
        return f.rect.x, f.rect.y, f.rect.width, f.rect.height
    else:
        # This is less reliable and also rises deprecation warnings;
        # wish I knew a better way to do it with GTK for multi-headed setups.
        # If window just opened, screen.get_active_window() may return None, so we need to retry.
        screen = win.get_screen()
        try:
            display_number = screen.get_monitor_at_window(screen.get_active_window())
            rectangle = screen.get_monitor_geometry(display_number)
            return rectangle.x, rectangle.y, rectangle.width, rectangle.height
        except:
            return 0, 0, 0, 0


def build_bar():
    icon_theme = Gtk.IconTheme.get_default()
    orientation = Gtk.Orientation.VERTICAL if args.vertical else Gtk.Orientation.HORIZONTAL
    box = Gtk.Box(orientation=orientation)

    appendix = load_json(build_from_file)
    for entry in appendix:
        name = entry["name"]
        exec = entry["exec"]
        icon = entry["icon"]
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

        button = Gtk.Button()
        button.set_property("name", "button")
        button.set_always_show_image(True)
        button.set_image(image)
        button.set_image_position(Gtk.PositionType.TOP)
        button.set_label(name)
        button.set_property("width_request", args.bw)
        button.set_property("height_request", args.bh)
        button.connect('clicked', launch, exec)
        box.pack_start(button, False, False, int(args.p / 2))

    return box


def launch(item, command):
    # run the command an quit
    subprocess.Popen('exec {}'.format(command), shell=True)
    Gtk.main_quit()


if __name__ == "__main__":
    main()
