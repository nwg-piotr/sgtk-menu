# Screenshots

`sgtk-menu -a -f -b -y 30`

![screen1](http://nwg.pl/Lychee/uploads/big/4fa362a554cc8f487dedc1e447b29089.png)

`sgtk-menu -af appendix-swaynagmode -n -b -y 30 -o 0.7`

![screen2](http://nwg.pl/Lychee/uploads/big/18ece77218aaf1d456927848a0ad1d33.png)

`sgtk-menu -a -f -y 30 -l fr`

![screen3](http://nwg.pl/Lychee/uploads/big/dd848b027b6a261e5f3391537644a88e.png)

`sgtk-menu -f -c`

![screen4](http://nwg.pl/Lychee/uploads/big/b20f0762fd33bb7e68f0988f116c9de8.png)

`sgtk-menu -n -c -o 0.7`

![screen5](http://nwg.pl/Lychee/uploads/big/43d581cb405fe74196458044092fe72b.png)

As a replacement to Openbox menu:

```xml
<mousebind action="Press" button="Right">
  <action name="Execute">
    <command>sgtk-menu -af appendix-ob -fn 5</command>
  </action>
</mousebind>
```

![screen6](http://nwg.pl/Lychee/uploads/big/2550116862b24aa43de179283487702a.png)

Horizontal button bar on sway, bound to mod+x:

`bindsym $mod+x exec sgtk-bar -o 0.7`

![screen7](http://nwg.pl/Lychee/uploads/big/e2d600d32e4bc0c8458fbe85c8428853.png)