# sgtk-menu
This project is an attempt to create a simple menu, that behaves decently on **sway**, but also on **i3** window manager. 
The menu may also be used in some **floating WMs**, but I only use Openbox, and don't test it elsewhere.

**sgtk-menu uses `pygobject` to create a themeable, searchable, gtk3-based system menu w/ some optional features**.

## Features

- `.desktop` entries-based system menu;
- search box to find what you need quickly;
- favourites (most frequently used entries) menu above (optional `[-f | -fn FN]` argument);
- user-defined menu below (optional `[-a | -af AF]` argument).

As the script searches `.desktop` files only, it may be used as a replacement to wofi/rofi `--drun`, but not to 
`--dmenu` mode.

![screenshot](http://nwg.pl/Lychee/uploads/big/c396d7eea8fc5c9c931f63b75940fb26.png)
*The menu in Arc-Dark GTK theme w/ Aqatix icons*

## Background

Well, I didn't even think that sway needed a menu, being happy with [wofi](https://hg.sr.ht/~scoopta/wofi) and 
[dmenu-wayland](https://github.com/nyyManni/dmenu-wayland). I started coding just to find out what the 
[Desktop Menu Specification](https://specifications.freedesktop.org/menu-spec/latest) looks like, and also to learn some 
more [pygobject](https://pygobject.readthedocs.io/en/latest). [The best menu I know](https://github.com/johanmalm/jgmenu), 
however, does not (yet?) behave well on sway. So, I thought to share the code, which has already taken me more time 
that I had ever expected.

[This code](https://github.com/johanmalm/jgmenu/blob/master/contrib/pmenu/jgmenu-pmenu.py) by 
[Johan Malm](https://github.com/johanmalm) helped me understand how to make use of `.desktop` entries. Many thanks!

## Usage

```text
$ sgtk-menu -h
usage: sgtk-menu [-h] [-b | -c] [-f | -fn FN] [-a | -af AF] [-n] [-l L] [-s S] [-w W] [-d D] [-o O]
                    [-t T] [-y Y]

GTK menu for sway, i3 and some floating WMs

optional arguments:
  -h, --help        show this help message and exit
  -b, --bottom      display menu at the bottom (sway & i3 only)
  -c, --center      center menu on the screen (sway & i3 only)
  -f, --favourites  prepend 5 most used items
  -fn FN            prepend <FN> most used items
  -a, --append      append custom menu from ~/.config/sgtk-menu/appendix
  -af AF            append custom menu from ~/.config/sgtk-menu/<AF>
  -n, --no-menu     skip menu, display appendix only
  -l L              force language (e.g. "de" for German)
  -s S              menu icon size (min: 16, max: 48, default: 20)
  -w W              menu width in px (integer, default: screen width / 8)
  -d D              menu delay in milliseconds (default: 100; sway & i3 only)
  -o O              overlay opacity (min: 0.0, max: 1.0, default: 0.3; sway & i3 only)
  -t T              sway submenu lines limit (default: 30)
  -y Y              y offset from edge to display menu at (sway & i3 only)
  -css CSS          use alternative ~/.config/sgtk-menu/<CSS> style sheet instead of
                    style.css
```

### Positioning

On **sway and i3** the default menu position it top left corner. Use `-b` or `-c` to place it at the bottom or in the 
center of the screen. Use `[-y <Y>]` argument to add a vertical offset from the edge.

On **floating WMs** the `-b` and `-c` arguments will be ignored. The menu position will always follow the mouse pointer,
provided that you installed the `python-pynput` package. Also the `-d | delay` argument takes no effect in floating WMs.

Sample **sway key binding**:

`bindsym mod1+F1 exec sgtk-menu -f -a`

Sample **i3 key binding**:

`bindsym Mod1+F1 exec --no-startup-id sgtk-menu -f -af appendix-i3`

The command menu prepended with the default number of favourites, appended with the proper custom menu template. 

To use sgtk-menu as a **replacement to Openbox menu**, you need to edit the mouse right click binding, e.g. like this:

```xml
<mousebind action="Press" button="Right">
  <action name="Execute">
    <command>sgtk-menu -f -af appendix-ob</command>
  </action>
</mousebind>
```

See [screenshots](https://github.com/nwg-piotr/sgtk-menu/tree/master/screenshots) for more examples.

## Installation

[![Packaging status](https://repology.org/badge/vertical-allrepos/sgtk-menu.svg)](https://repology.org/project/sgtk-menu/versions)

For now the only available package is [sgtk-menu](https://aur.archlinux.org/packages/sgtk-menu) [AUR] for Arch linux.
However, you may simply clone the repository and launch the `sgtk-menu.py` file, instead of `sgtk-menu` command.

## Dependencies

- `gtk3`
- `python` (python3)
- `python-gobject`
- `python-cairo` | `python-cairocffi `
- `python-i3ipc`
- `python-pynfo`: *optional for positioning in floating WMs*

## How it works on sway & i3?

The problem to resolve was, that the Gtk.Menu class behaves differently / unexpectedly when open over Wayland and X11 windows. 
To work it around, the script opens the menu over a (semi-)transparent, floating window, that covers all the screen.

## Configuration

All custom menus and .css style sheets must be placed in `/your/confid/dir/sgtk-menu/` (usually `~/.config/sgtk-menu/`). 
Whatever you specify with arguments, are file names, not paths.

### Appendix

Appendix is a custom menu in json format, in the `/your/confid/dir/appendix` file, or another, forced with the 
`-af <filename>` argument.

### Styling

You may use the `~/.config/sgtk-menu/style.css` file, or another one, forced with the `-css <filename>` argument) to 
override some theme settings, e.g.:

```text
#menu {
    font-family: monospace;
    background: #ede9e0
}

#submenu {
    background: #ede9e0
}

#item-category:hover {
    background: #6a3513
}

#item-favorites:hover {
    background: #6a3513
}

#item:hover {
    background: #6a3513
}

#separator {
    margin: 10px;
}
```

Widgets are named as below:

![css-styling](http://nwg.pl/Lychee/uploads/big/3e2faa61abc70c89e277b7a54aa8e392.png)

## i3 support, floating WMs support

Even if there exist plenty of good X11 menus, with the most excellent [jgmenu](https://github.com/johanmalm/jgmenu) 
on top, I'm doing my best to make sgtk-menu i3-compatible. It's also possible to use sgtk-menu in some floating window 
managers, e.g. to replace the Openbox / Fluxbox menu. See below to resolve issues, if any. 

## Troubleshooting

### [sway] Submenu not scrollable

This is a bug either in sway 1.2, or GTK: if the menu height exceeds the screen height, it becomes partially unresponsive.
The script uses a ~~tricky as hell~~ workaround, but you must specify how many entries fit in your screen vertically.
By default it's 30. If it's too much to your screen, try the `-t <T>` argument w/ a value < 30.

### [sway, i3] Menu does not position properly in the screen corner

Try increasing the delay length. The default value is 100 milliseconds, and on my laptop it works well down to 30. 
Slower machines, however, may require higher values. E.g. try using `-d 200` argument.

### [i3] Overlay behind the menu is not (semi)transparent

You need [compton](https://github.com/chjj/compton) or equivalent X11 compositor.

### [i3] Overlay first displays as a tiled window

Add this to your `~/.config/i3/config` file:

```text
for_window [title="~sgtk-"] border none, floating enable
```

### [Openbox] The menu always appears in the top left corner

You need the `pynput` python module. Install optional `python-pynput` package or use `PIP`.

## TODO
- On next sway / GTK release, check if the overflowed menus issue on sway is fixed; remove 50 SLOC long workaround if so;
- testing;
- more testing.
