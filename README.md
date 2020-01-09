# sway-gtk-menu
This project is an attempt to create a simple system menu, that behaves decently on sway and i3 window managers. 
It uses `pygobject` to create a gtk3-based system menu. It's possible to append user-defined (json) entries at the bottom.
The menu also implements the Search feature.

The script searches `.desktop` files, so ma be used a replacement to wofi/rofi --drun, but not for --dmenu mode.

Well, I didn't even think that sway needed a menu, being actually happy with [wofi](https://hg.sr.ht/~scoopta/wofi) and 
[dmenu-wayland](https://github.com/nyyManni/dmenu-wayland). I started coding just to find out what the freedesktop 
[Desktop Menu Specification](https://specifications.freedesktop.org/menu-spec/latest) looks like, and also to learn some 
more [pygobject](https://pygobject.readthedocs.io/en/latest).

[The best menu I know](https://github.com/johanmalm/jgmenu), however, does not (yet?) behave well on sway. So, I thought
to share the code, which has already taken me more time that I had ever expected.

[This code](https://github.com/johanmalm/jgmenu/blob/master/contrib/pmenu/jgmenu-pmenu.py) by 
[Johan Malm](https://github.com/johanmalm) helped me understand how to make use of `.desktop` entries. Many thanks!

![screenshot](http://nwg.pl/Lychee/uploads/big/17ac6bb99f50f8669c0df65a755e80cb.png)

```text
$ /path/to/the/script/menu.py -h
usage: menu.py [-h] [-b] [-a] [-l L] [-s S] [-w W] [-d D] [-o O]

A simple menu for sway and i3

optional arguments:
  -h, --help    show this help message and exit
  -b, --bottom  display at the bottom
  -a, --append  append menu from /home/piotr/.config/sway-gtk-menu/appendix
  -l L          force language (str, like "en" for English)
  -s S          menu icon size (int, min: 16, max: 48, default: 20)
  -w W          menu width in px (int, default: screen width / 8)
  -d D          menu delay in milliseconds (int, default: 50)
  -o O          overlay opacity (float, min: 0.0, max: 1.0, default: 0.3)
```

## Dependencies
- gtk3
- python (python3)
- python-gobject
- python-i3ipc (optionally)

## How it works?

The problem to resolve was, that Gtk.Menu behaves differently / unexpectedly when open over Wayland and X11 windows. 
To avoid it, the script first creates a (semi-)transparent, floating window, that covers all the screen.

## Troubleshooting

In case the menu does not position properly in the screen corner, try increasing the delay length. The default value
equals 50 milliseconds, and on my machine it works well down to 30, but slower machines may require higher values.
E.g. use `-d 100` argument.

## TODO
- Resolve the missing submenus overflow arrows issue on sway;
- consider adding "latest" cache to prepend the menu with several lately / frequently used entries (?).
