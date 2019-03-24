#!/usr/bin/python3
# Copyright (c) 2017-2019 David Steele <dsteele@gmail.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later
# License-Filename: LICENSE

#
# Copyright 2016-2017 David Steele <steele@debian.org>
# This file is part of comitup
# Available under the terms of the GNU General Public License version 2
# or later
#

import dbus
import NetworkManager

from gi.repository.GLib import MainLoop

from dbus.mainloop.glib import DBusGMainLoop

import logging

if __name__ == '__main__':
    DBusGMainLoop(set_as_default=True)

if __name__ == '__main__':
    import os, sys
    fullpath = os.path.abspath(__file__)
    parentdir = '/'.join(fullpath.split('/')[:-2])
    sys.path.insert(0, parentdir)

from comitup import nm       # noqa
from comitup import modemgr  # noqa

log = logging.getLogger('comitup')

bus = dbus.SystemBus()
main_loop = None

monitored_dev = None
ap_device = None
second_device = None

paths = []

nm_dev_connect = None
nm_dev_fail = None

PASS_STATES = [nm.NM_DEVICE_STATE_IP_CHECK, nm.NM_DEVICE_STATE_ACTIVATED]
FAIL_STATES = [nm.NM_DEVICE_STATE_FAILED]


def disable():
    global monitored_dev, nm_dev_connect, nm_dev_fail

    monitored_dev = None

    nm_dev_connect = None
    nm_dev_fail = None


def enable(dev, connect_fn, fail_fn):
    global monitored_dev, nm_dev_connect, nm_dev_fail

    monitored_dev = None

    nm_dev_connect = connect_fn
    nm_dev_fail = fail_fn

    monitored_dev = dev


def ap_changed_state(state, *args):
    try:
        if monitored_dev == ap_device:
            if state in PASS_STATES:
                nm_dev_connect()
            elif state in FAIL_STATES:
                nm_dev_fail()
    except:
        pass


def second_changed_state(state, *args):
    try:
        if monitored_dev == second_device:
            if state in PASS_STATES:
                nm_dev_connect()
            elif state in FAIL_STATES:
                nm_dev_fail()
    except:
        pass


def set_device_listeners(ap_dev, second_dev):
    global ap_device, second_device, paths

    ap_device = ap_dev
    path = nm.get_device_path(ap_dev)
    device_listener = bus.add_signal_receiver(
        ap_changed_state,
        signal_name="StateChanged",
        dbus_interface="org.freedesktop.NetworkManager.Device",
        path=path
    )
    paths.append(path)

    if second_dev != ap_dev:
        second_device = second_dev
        path = nm.get_device_path(second_dev)
        device_listener = bus.add_signal_receiver(
            second_changed_state,
            signal_name="StateChanged",
            dbus_interface="org.freedesktop.NetworkManager.Device",
            path=path
        )
        paths.append(path)


def nuke_from_orbit():
    for dev in ap_device, second_device:
        if dev:
            dev.Disconnect()

    main_loop.quit()


def device_added(path):
    device = NetworkManager.Device(path)
    if type(device).__name__ == "Wireless":
        log.error("A WiFi device has become available. Restarting")
        nuke_from_orbit()


def device_removed(path):
    if path in paths:
        log.error("A Wifi device has been removed. Restarting")
        nuke_from_orbit()


def init_nmmon(loop):
    global main_loop
    main_loop = loop

    bus.add_signal_receiver(
        device_added,
        signal_name="DeviceAdded",
        dbus_interface="org.freedesktop.NetworkManager"
    )

    bus.add_signal_receiver(
        device_removed,
        signal_name="DeviceRemoved",
        dbus_interface="org.freedesktop.NetworkManager"
    )

    set_device_listeners(
        modemgr.get_ap_device(),
        modemgr.get_link_device()
    )


def main():
    handler = logging.StreamHandler(stream=None)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    log.info('starting')

    loop = MainLoop()
    init_nmmon(loop)

    def up():
        print("wifi up")

    def down():
        print("wifi down")

    enable(modemgr.get_ap_device(), up, down)

    loop.run()


if __name__ == '__main__':
    main()
