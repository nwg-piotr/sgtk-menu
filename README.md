# sway-gtk-menu
This project is an attempt to create a **simple** menu, that behaves decently on sway window manager. 
It uses `pygobject` to create a gtk3-based system menu.

Well, I didn't even think that sway needed a menu, as I'm really happy with [wofi](https://hg.sr.ht/~scoopta/wofi) and/or 
[dmenu-wayland](https://github.com/nyyManni/dmenu-wayland). I started coding just to find out what the freedesktop 
[Desktop Menu Specification](https://specifications.freedesktop.org/menu-spec/latest) looks like, and also to learn some 
more [pygobject](https://pygobject.readthedocs.io/en/latest).

[The best menu I know](https://github.com/johanmalm/jgmenu), however, does not (yet?) behave well on sway. So, I thought
to share the code, which already took me more time that I had ever expected.

[This code](https://github.com/johanmalm/jgmenu/blob/master/contrib/pmenu/jgmenu-pmenu.py) by 
[Johan Malm](https://github.com/johanmalm) helped me understand how to make use of `.desktop` entries. Many thanks!

![screenshot](http://nwg.pl/Lychee/uploads/big/0d985b5db7bfd378c5b484562fd330cf.png)


