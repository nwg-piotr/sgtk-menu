# sway-gtk-menu
This project is an attempt to create a **simple** menu, that behaves decently on sway window manager. 
It uses `pygobject` to create a gtk3-based system menu. It's still a work in progress: 
see [TODO](https://github.com/nwg-piotr/sway-gtk-menu/tree/master#todo).

Well, I didn't even think that sway needed a menu, as I'm really happy with [wofi](https://hg.sr.ht/~scoopta/wofi) and 
[dmenu-wayland](https://github.com/nyyManni/dmenu-wayland). I started coding just to find out what the freedesktop 
[Desktop Menu Specification](https://specifications.freedesktop.org/menu-spec/latest) looks like, and also to learn some 
more [pygobject](https://pygobject.readthedocs.io/en/latest).

[The best menu I know](https://github.com/johanmalm/jgmenu), however, does not (yet?) behave well on sway. So, I thought
to share the code, which has already taken me more time that I had ever expected.

[This code](https://github.com/johanmalm/jgmenu/blob/master/contrib/pmenu/jgmenu-pmenu.py) by 
[Johan Malm](https://github.com/johanmalm) helped me understand how to make use of `.desktop` entries. Many thanks!

![screenshot](http://nwg.pl/Lychee/uploads/big/0d985b5db7bfd378c5b484562fd330cf.png)

```text
$ /path/to/the/script/menu.py -h
usage: menu.py [-h] [-b] [-r] [-s S] [-d D] [-o O]

A simple sway menu

optional arguments:
  -h, --help    show this help message and exit
  -b, --bottom  display at the bottom
  -r, --right   display on the right side
  -s S          menu icon size (int, min: 16, max: 48, def: 20)
  -d D          menu delay in milliseconds (int, def: 50)
  -o O          overlay opacity (float, min: 0.0, max: 1.0, def: 0.3)
```

## Dependencies
- gtk3
- python (python3)
- python-gobject
- python-i3ipc (optionally)

## How it works?

The problem to resolve was, that Gtk.Menu behaves differently / unexpectedly when open over Wayland and X11 windows. 
To avoid it, the script first creates a (semi-)transparent, floating window, that covers all the screen.

## TODO
- Add support for localization;
- resolve the missing overflow marks issue on sway;
- either improve or give up on i3 support.
