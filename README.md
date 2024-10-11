# sgtk-menu

## This project is archival

This project was my first attempt to launchers development. The code has been later reused and significantly improved
in other projects. **I no longer work on sgtk-menu**. Please use launchers named below instead:

### [nwg-launchers](https://github.com/nwg-piotr/nwg-launchers)

C++ version of the launchers provided by sgtk-menu. It works as well on wlroots-based compositors, as on X11. 
The project is community-driven, as I turned out to be a hopeless C++ programmer. I no longer maintain this code, 
please use nwg-drawer, nwg-menu and nwg-dock instead.

### [nwg-shell](https://github.com/nwg-piotr/nwg-shell)

GTK-based shell for sway and Hyprland. The project includes a panel and a set of launchers, developed in
Python and Go, that may also be used standalone. The nwg-shell project is under active development.

## The description below is archival as well

This project is an attempt to create a launcher, that behaves decently on **sway**, but also works on other window 
managers. It may or may not work on some DEs - I don't care much about it. For what I managed to test so far, 
see the [Compatibility chart](https://github.com/nwg-piotr/sgtk-menu/wiki/Compatibility-chart).

**sgtk-menu uses `pygobject` to create a themeable, searchable, gtk3-based system launchers w/ some optional features:**

- `.desktop` entries-based system menu;
- search box to find what you need quickly;
- favourites (most frequently used entries) menu above (optional `[-f | -fn FN]` argument);
- user-defined menu below (optional `[-a | -af AF]` argument);
- `sgtk-dmenu` command: search and run commands in `$PATH`;
- `sgtk-bar` command: user-defined horizontal or vertical button bar;
- `sgtk-grid` command: a GNOME-like application grid.

Read [wiki](https://github.com/nwg-piotr/sgtk-menu/wiki) for more information. 
See [screenshots](https://github.com/nwg-piotr/sgtk-menu/tree/master/screenshots) 
for usage examples.

## Background

Well, I didn't even think that sway needed a menu, being happy with [wofi](https://hg.sr.ht/~scoopta/wofi) and 
[dmenu-wayland](https://github.com/nyyManni/dmenu-wayland). I started coding just to find out what the 
[Desktop Menu Specification](https://specifications.freedesktop.org/menu-spec/latest) looks like, and also to learn some 
more [pygobject](https://pygobject.readthedocs.io/en/latest). The best menu I know, however, does not (yet?) behave well 
on sway. So, I thought to share the code, which has already taken me more time that I had ever expected.

[This code](https://github.com/johanmalm/jgmenu/blob/master/contrib/pmenu/jgmenu-pmenu.py) by 
[Johan Malm](https://github.com/johanmalm) helped me understand how to make use of `.desktop` entries. Many thanks!

## How it works on sway

The problem to resolve on sway, was, that the Gtk.Menu class behaves differently / unexpectedly when open over Wayland and X11 windows. 
To work it around, the script opens the menu over a (semi-)transparent, floating window, that covers all the screen.

## Packaging status

[![Packaging status](https://repology.org/badge/vertical-allrepos/sgtk-menu.svg)](https://repology.org/project/sgtk-menu/versions)

### Arch Linux

Install [sgtk-menu](https://aur.archlinux.org/packages/sgtk-menu) from AUR.

### Fedora

`sudo dnf install sgtk-menu`

See [wiki](https://github.com/nwg-piotr/sgtk-menu/wiki/Installation) for more info.
