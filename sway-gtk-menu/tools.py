#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

"""
This code is heavily influenced by Johan Malm's
https://github.com/johanmalm/jgmenu/blob/master/contrib/pmenu/jgmenu-pmenu.py

Copyright (C) 2016-2017 Ovidiu M <mrovi9000@gmail.com>
Copyright (C) 2017-2019 Johan Malm <jgm323@gmail.com>
Copyright (C) 2020 Piotr Miller <nwg.piotr@gmail.com>
"""
import os
import locale


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
    defined_names = {}
    for d in settings_dirs():
        d = d + "/desktop-directories/"
        for (dirpath, dirnames, filenames) in os.walk(d):
            for filename in filenames:
                name, localized_name = read_entry(os.path.join(dirpath, filename), lang)
                if name and localized_name and name not in defined_names:
                    defined_names[name] = localized_name
                    if additional_to_main(name) not in defined_names:
                        defined_names[additional_to_main(name)] = localized_name

    if "Other" not in defined_names:
        defined_names["Other"] = "Other"

    return defined_names


def read_entry(path, lang):
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


def settings_dirs():
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
