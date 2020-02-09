#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

"""
Most part of this code is heavily influenced by Johan Malm's
https://github.com/johanmalm/jgmenu/blob/master/contrib/pmenu/jgmenu-pmenu.py

Copyright (C) 2016-2017 Ovidiu M <mrovi9000@gmail.com>
Copyright (C) 2017-2019 Johan Malm <jgm323@gmail.com>
Copyright (C) 2020 Piotr Miller <nwg.piotr@gmail.com>
"""
import os
import subprocess
import shutil
import locale
import json
import pkg_resources


def check_wm():
    env = os.environ
    for key in env:
        if key == "DESKTOP_SESSION":
            if env[key].endswith("sway"):
                return "sway"
            elif env[key].endswith("i3"):
                return "i3"
            elif env[key].endswith("openbox"):
                return "openbox"
        elif key == "I3SOCK":
            if "sway" in env[key]:
                return "sway"
            elif "i3" in env[key]:
                return "i3"
    try:
        if subprocess.run(
                ['swaymsg', '-t', 'get_seats'], stdout=subprocess.DEVNULL).returncode == 0:
            return "sway"
    except:
        pass

    try:
        if subprocess.run(['i3-msg', '-t', 'get_outputs'], stdout=subprocess.DEVNULL).returncode == 0:
            return "i3"
    except:
        pass
    
    return "other"


def display_geometry(win, wm, mouse_pointer):
    """
    Returns geometry of currently focused display
    :return: (x, y, width, height)
    """
    if wm == "sway":
        string = subprocess.getoutput("swaymsg -t get_outputs")
        outputs = json.loads(string)
        for i in range(len(outputs)):
            if outputs[i]["focused"]:
                rect = outputs[i]["rect"]
                return rect["x"], rect["y"], rect["width"], rect["height"]
    elif wm == "i3":
        # Unfortunately `i3-msg -t get_outputs` output does not have the "focused" key.
        # Let's find the active workspace and its rectangle.
        string = subprocess.getoutput("i3-msg -t get_workspaces")
        workspaces = json.loads(string)
        for i in range(len(workspaces)):
            if workspaces[i]['focused']:
                rect = workspaces[i]["rect"]
                return rect["x"], rect["y"], rect["width"], rect["height"]
    else:
        # For not sway nor i3. This rises deprecation warnings and won't work w/o `pynput` module.
        # If window just opened, screen.get_active_window() may return None, so we need to retry.
        # Wish I knew a better way to do it with GTK for multi-headed setups. Anyone?
        screen = win.get_screen()
        try:
            if mouse_pointer:
                x, y = mouse_pointer.position
                display_number = screen.get_monitor_at_point(x, y)
            else:
                # If pynput missing, the bar will always appear at top left corner of the screen w/ active window.
                display_number = screen.get_monitor_at_window(screen.get_active_window())
            rectangle = screen.get_monitor_geometry(display_number)
            return rectangle.x, rectangle.y, rectangle.width, rectangle.height
        except:
            return 0, 0, 0, 0


def get_locale_string(forced_lang=None):
    if forced_lang:
        language = forced_lang.split("_")[0]
    else:
        language = locale.getlocale()[0] or "en_US"
    lang = language.split("_")[0]
    if lang:
        return '[{}]'.format(lang)
    else:
        return None


def localized_category_names(lang='en'):
    """
    :param lang: detected or forced locale
    :return: dictionary: category name => translated category name
    """
    defined_names = {}
    for d in data_dirs():
        d = d + "/desktop-directories/"
        for (dir_path, dir_names, file_names) in os.walk(d):
            for filename in file_names:
                name, localized_name = translate_name(os.path.join(dir_path, filename), lang)
                if name and localized_name and name not in defined_names:
                    defined_names[name] = localized_name
                    if additional_to_main(name) not in defined_names:
                        defined_names[additional_to_main(name)] = localized_name

    if "Other" not in defined_names:
        defined_names["Other"] = "Other"

    return defined_names


def translate_name(path, lang):
    name, localized_name = None, None
    try:
        with open(path) as d:
            lines = d.readlines()
            for line in lines:
                if line.startswith("["):
                    read_me = line.strip() == "[Desktop Entry]"
                    continue
                if read_me:
                    if line.startswith('Name='):
                        name = line.split('=')[1].strip()
                    if lang != '[en]':
                        if line.startswith('Name{}='.format(lang)):
                            localized_name = line.split('=')[1].strip()
                    else:
                        localized_name = name
    except:
        pass
    return name, localized_name


def data_dirs():
    paths = [os.path.expanduser('~/.local/share'), "/usr/share", "/usr/local/share"]
    if "XDG_DATA_DIRS" in os.environ:
        dirs = os.environ["XDG_DATA_DIRS"]
        if dirs:
            dirs = dirs.split(":")
            for d in dirs:
                while d.endswith("/"):
                    d = d[:-1]
                if d not in paths:
                    paths.append(d)
    return paths


def path_dirs():
    paths = []
    if "PATH" in os.environ:
        dirs = os.environ["PATH"]
        if dirs:
            dirs = dirs.split(":")
            for d in dirs:
                while d.endswith("/"):
                    d = d[:-1]
                if d not in paths:
                    paths.append(d)
    return paths


def config_dirs():
    paths = [os.path.join(os.path.expanduser('~/.config'), 'sgtk-menu')]
    if "XDG_CONFIG_HOME" in os.environ:
        paths.append(os.path.join(os.environ["XDG_CONFIG_HOME"], 'sgtk-menu'))
    return paths


def additional_to_main(category):
    """
    See https://specifications.freedesktop.org/menu-spec/latest/apas02.html
    """
    if category == 'AudioVideo' or category in ['Audio', 'Video', 'Midi', 'Mixer', 'Sequencer', 'Tuner', 'TV',
                                                'AudioVideoEditing', 'Player', 'Recorder', 'DiscBurning', 'Music',
                                                'Sound & Video']:
        return 'AudioVideo'

    elif category == 'Development' or category in ['Building', 'Debugger', 'IDE', 'GUIDesigner', 'Profiling',
                                                   'RevisionControl', 'Translation', 'WebDevelopment', 'Programming']:
        return 'Development'

    elif category == 'Game' or category in ['ActionGame', 'AdventureGame', 'ArcadeGame', 'BoardGame', 'BlocksGame',
                                            'CardGame', 'KidsGame', 'LogicGame', 'RolePlaying', 'Shooter', 'Simulation',
                                            'SportsGame', 'StrategyGame', 'Emulator', 'Games']:
        return 'Game'

    elif category == 'Graphics' or category in ['2DGraphics', 'VectorGraphics', 'RasterGraphics', '3DGraphics',
                                                'Scanning', 'OCR', 'Photography']:
        return 'Graphics'

    elif category == 'Network' or category in ['Dialup', 'InstantMessaging', 'Chat', 'IRCClient', 'Feed',
                                               'FileTransfer', 'HamRadio', 'News', 'P2P', 'RemoteAccess', 'Telephony',
                                               'VideoConference', 'WebBrowser', 'Internet', 'Internet and Network']:
        return 'Network'

    elif category == 'Office' or category in ['Calendar', 'ContactManagement', 'Database', 'Dictionary', 'Chart',
                                              'Email', 'Finance', 'FlowChart', 'PDA', 'ProjectManagement',
                                              'Presentation', 'Spreadsheet', 'WordProcessor', 'Publishing', 'Viewer']:
        return 'Office'

    elif category == 'Science' or category in ['ArtificialIntelligence', 'Astronomy', 'Biology', 'Chemistry', 'Economy',
                                               'Electricity', 'Geography', 'Geology', 'Geoscience', 'History',
                                               'Humanities', 'MedicalSoftware', 'Physics', 'Robotics',
                                               'Science & Math', 'Spirituality', 'Art', 'Construction', 'Languages',
                                               'ComputerScience', 'DataVisualization', 'ImageProcessing', 'Literature',
                                               'Math', 'NumericalAnalysis', 'Sports', 'ParallelComputing', 'Education']:
        return 'Science'

    elif category == 'Settings' or category in ['Preferences', 'DesktopSettings', 'HardwareSettings', 'PackageManager',
                                                'Security', 'Accessibility', 'Administration', 'Hardware',
                                                'Look and Feel', 'Personal', 'Universal Access']:
        return 'Settings'

    elif category == 'System' or category in ['FileTools', 'FileManager', 'TerminalEmulator', 'Filesystem', 'Monitor',
                                              'System Tools']:
        return 'System'

    elif category == 'Utility' or category in ['TextTools', 'TelephonyTools', 'Maps', 'Archiving', 'Compression',
                                               'Calculator', 'Clock', 'TextEditor', 'Accessories']:
        return 'Utility'

    elif category == 'Other' or category in ['Programs']:
        return 'Other'

    else:
        return None


def create_default_configs(config_dir):
    # Create default config files if not found
    src_files = pkg_resources.resource_listdir('sgtk_menu', 'config')
    for file_name in src_files:
        dst_file = os.path.join(config_dir, file_name)
        if not os.path.isfile(dst_file):
            src_file = os.path.join('config', file_name)
            # Use stream copy, in case of zip egg packaging.
            fsrc = pkg_resources.resource_stream('sgtk_menu', src_file)
            with open(dst_file, 'wb') as fdst:
                shutil.copyfileobj(fsrc, fdst)


def load_json(path):
    """
    :return: dictionary
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(e)
        return {}


def save_json(src_dict, path):
    with open(path, 'w') as f:
        json.dump(src_dict, f, indent=2)


def print_version():
    try:
        version = pkg_resources.require('sgtk-menu')[0].version
    except Exception as e:
        version = 'unknown version ({})'.format(e)
    print('\nsgtk-menu {}'.format(version))
    print('Copyright (c) 2020 Piotr Miller & Contributors')
