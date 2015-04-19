#!/usr/bin/env python

import os
import subprocess
import time

# assume BuildRaspbianVc4.py is in the same dir as this one 
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PREFIX = time.strftime("%Y%m%d-%H%M-vc4")
UPLOAD_HOST = "sukzessiv.net"
UPLOAD_USER = "vc4-buildbot"
UPLOAD_KEY = os.path.dirname(os.path.realpath(__file__)) + "/sukzessiv-net.pem"
UPLOAD_PATH = "~/upload/"
# this can be determined from fdisk *.img
RASPBIAN_IMG_BYTES_PER_SECTOR = 512
RASPBIAN_IMG_START_SECTOR_VFAT = 8192
RASPBIAN_IMG_START_SECTOR_EXT4 = 122880

def checkRoot():
	if os.geteuid() != 0:
		exit("You need to have root privileges to run this script")

def killHangingBuilds():
	subprocess.call("pkill -f \"BuildRaspbianVc4\"", shell=True)

def UploadTempFiles():
	# XXX: disable host check? or http://serverfault.com/questions/132970/can-i-automatically-add-a-new-host-to-known-hosts
	# XXX: add *.pem to .gitignore
	ret = subprocess.call("scp -Bpq -i " + UPLOAD_KEY + " /tmp/*-vc4* " + UPLOAD_USER + "@" + UPLOAD_HOST + ":" + UPLOAD_PATH, shell=True)
	return ret

def DeleteTempFiles():
	subprocess.call("rm -f /tmp/*-vc4*", shell=True)

def BuildRaspbianVc4():
	ret = subprocess.call(SCRIPT_DIR + "/BuildRaspbianVc4.py >/tmp/" + PREFIX + ".log 2>&1", shell=True)
	if not ret:
		subprocess.call("mv /tmp/" + PREFIX + ".log /tmp/" + PREFIX + "-success.log", shell=True)
		subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-success.log", shell=True)
		subprocess.call("cp /boot/issue-vc4.json /tmp/" + PREFIX + "-issue.json", shell=True)
	else:
		subprocess.call("mv /tmp/" + PREFIX + ".log /tmp/" + PREFIX + "-failure.log", shell=True)
		subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-failure.log", shell=True)
	return ret

def TarRaspbianVc4():
	# XXX: optionally include src
	# XXX: better to temp. move original dir?
	subprocess.call("tar cfp /tmp/" + PREFIX + "-overlay.tar /boot/bcm2708-rpi-b.dtb /boot/bcm2708-rpi-b-plus.dtb /boot/bcm2709-rpi-2-b.dtb /boot/config.txt /boot/issue-vc4.json /boot/kernel.img /boot/kernel.img-config /boot/kernel7.img /boot/kernel7.img-config /etc/ld.so.conf.d/01-libc.conf /lib/modules/*-raspbian-* /usr/local --exclude=\"/usr/local/bin/indiecity\" --exclude=\"/usr/local/games\" --exclude=\"/usr/local/lib/python*\" --exclude=\"/usr/local/lib/site_ruby\" --exclude=\"/usr/local/src\" --exclude=\"/usr/local/sbin\" --exclude=\"/usr/local/share/applications\" --exclude=\"/usr/local/share/ca-certificates\" --exclude=\"/usr/local/share/fonts\" --exclude=\"/usr/local/share/sgml\" --exclude=\"/usr/local/share/xml\" >/dev/null", shell=True)
	subprocess.call("bzip2 -9 /tmp/" + PREFIX + "-overlay.tar", shell=True)
	return "/tmp/" + PREFIX + "-overlay.tar.bz2"

def BuildRaspbianImage(overlay):
	subprocess.check_call("apt-get -y install zip", shell=True)
	os.chdir("/tmp")
	# make sure we have the latest version
	subprocess.call("wget -N http://downloads.raspberrypi.org/raspbian_latest", shell=True)
	subprocess.check_call("rm -Rf /tmp/raspbian-vc4", shell=True)
	subprocess.check_call("mkdir /tmp/raspbian-vc4", shell=True)
	os.chdir("/tmp/raspbian-vc4")
	subprocess.check_call("unzip ../raspbian_latest", shell=True)
	# this should yield one .img file inside /tmp/raspbian-vc4
	subprocess.check_call("mkdir /tmp/raspbian-vc4/live", shell=True)
	subprocess.check_call("mount -o offset=" + str(RASPBIAN_IMG_START_SECTOR_EXT4 * RASPBIAN_IMG_BYTES_PER_SECTOR) + " -t ext4 *.img live", shell=True)
	subprocess.check_call("mount -o offset=" + str(RASPBIAN_IMG_START_SECTOR_VFAT * RASPBIAN_IMG_BYTES_PER_SECTOR) + " -t vfat *.img live/boot", shell=True)
	os.chdir("/tmp/raspbian-vc4/live")
	subprocess.check_call("tar vfxp " + overlay, shell=True)
	# enable sshd by default
	subprocess.check_call("ln -s ../init.d/ssh etc/rc2.d/S02ssh", shell=True)
	subprocess.check_call("ln -s ../init.d/ssh etc/rc3.d/S02ssh", shell=True)
	subprocess.check_call("ln -s ../init.d/ssh etc/rc4.d/S02ssh", shell=True)
	subprocess.check_call("ln -s ../init.d/ssh etc/rc5.d/S02ssh", shell=True)
	os.chdir("/tmp/raspbian-vc4")
	subprocess.check_call("umount live/boot", shell=True)
	subprocess.check_call("umount live", shell=True)
	subprocess.check_call("zip -9 ../" + PREFIX +"-image.zip *.img", shell=True)
	os.chdir("/tmp")
	subprocess.check_call("rm -Rf /tmp/raspbian-vc4", shell=True)
	# we keep raspbian_latest around for future invocations (although it looks like /tmp gets cleaned?)
	return "/tmp/" + PREFIX + "-image.zip"

# XXX: pull latest vc4-buildbot script
# XXX: umask?
# XXX: prepopulate ssh host keys in known_hosts
checkRoot()
killHangingBuilds()
UploadTempFiles()
DeleteTempFiles()
# preserve original kernel and device tree on build machine
subprocess.call("cp /boot/kernel.img /boot/kernel.img.orig", shell=True)
subprocess.call("cp /boot/bcm2708-rpi-b.dtb /boot/bcm2708-rpi-b.dtb.orig", shell=True)
subprocess.call("cp /boot/bcm2708-rpi-b-plus.dtb /boot/bcm2708-rpi-b-plus.dtb.orig", shell=True)
subprocess.call("cp /boot/kernel7.img /boot/kernel7.img.orig", shell=True)
subprocess.call("cp /boot/bcm2709-rpi-2-b.dtb /boot/bcm2709-rpi-2-b.dtb.orig", shell=True)
ret = BuildRaspbianVc4()
if not ret:
	# success
	tar = TarRaspbianVc4()
# restore original kernel
subprocess.call("mv /boot/kernel.img.orig /boot/kernel.img", shell=True)
subprocess.call("mv /boot/bcm2708-rpi-b.dtb.orig /boot/bcm2708-rpi-b.dtb", shell=True)
subprocess.call("mv /boot/bcm2708-rpi-b-plus.dtb.orig /boot/bcm2708-rpi-b-plus.dtb", shell=True)
subprocess.call("mv /boot/kernel7.img.orig /boot/kernel7.img", shell=True)
subprocess.call("cp /boot/bcm2709-rpi-2-b.dtb.orig /boot/bcm2709-rpi-2-b.dtb", shell=True)
if not ret:
	BuildRaspbianImage(tar)
ret = UploadTempFiles()
if not ret:
	DeleteTempFiles()
#else:
#	there might be a temporary connectivity issue
#	in this case we'll try again next time this script is run

# XXX: limit login to scp?
# XXX: delete old builds on the server
# XXX: ~/.ssh mode 700?
