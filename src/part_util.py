#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2012~2013 Deepin, Inc.
#               2012~2013 Long Wei
#
# Author:     Long Wei <yilang2007lw@gmail.com>
# Maintainer: Long Wei <yilang2007lw@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

TARGET="/target"
PART_TYPE_LIST=["primary","logical","extend","freespace","metadata","protect"]
import os
from basic_utils import get_os_command_oneput,run_os_command,get_os_command_output

import parted


class PartUtil:
    '''user interface communicate with backend via disk_partition_info_tab,mark each partition in the table:
    keep:the origin partition,we don't want and don't need to change
    add:new added partition,we should do add partition
    delete:to added partition,just remove from the table;else mark delete flag,then do real delete operation
    '''
    def __init__(self):
    #for temporay used variable    
        self.device=""
        self.devices=[]
        self.disk=""
        self.disks=[]
        self.partition=""
        self.partitions=[]
    #machine based:[disk,geometry,partition],to do the backend operations
        self.disk_partition_tab =[]
    #user based:(partition,part_disk_path,part_type,part_size,part_fs,part_format,part_name,part_mountpoint,part_flag),frontend 
        self.disk_partition_info_tab=[]


    #disk_partition_tab && disk_partition_info operations:
    def init_disk_partition_info_tab(self):
        '''read origin disk partition info'''
        
        for disk in self.get_system_disks():
            if disk.getFirstPartition()==None:
                self.set_disk_label(disk.device)
                continue 
            for part in self.get_disk_partitions(disk):
                self.partition=part
                self.part_disk_path=part.disk.device.path
                self.part_type=PART_TYPE_LIST[part.type]
                self.part_size=part.getSize(unit="MB")
                try:
                    self.part_fs=part.fileSystem.type#just for primary and logical partition
                except:
                    self.part_fs=None
                self.part_format=True
                self.part_name=part.name

                try:
                    self.part_mountpoint=self.get_disk_partition_mount(self.partition)[0][1]
                except:
                    self.part_mountpoint=""
                    
                self.part_flag="keep"   #flag:keep,new,delete 
                # self.disk_partition_info_tab_item=[self.partition.path,self.part_disk_path,self.part_type,
                #                                    self.part_size,self.part_fs,self.part_format,
                #                                    self.part_name,self.part_mountpoint]

                self.disk_partition_info_tab_item=[self.partition,self.part_disk_path,self.part_type,
                                                   self.part_size,self.part_fs,self.part_format,
                                                   self.part_name,self.part_mountpoint,self.part_flag]

                self.disk_partition_info_tab.append(self.disk_partition_info_tab_item)

        return self.disk_partition_info_tab

    def refresh_disk_partition_info_tab(self,disk_partition_info_tab):
        '''sort the table according to partition number,update the table after add or delete operation'''
        parts_path=[]
        for item in self.disk_partition_info_tab:
            parts_path.append(item[0].path)
        parts_path.sort()    
        return parts_path


    def get_disk_partition_object(self,part_disk_path,part_type,part_size,part_fs):
        '''get partition_object for add to the disk_partition_info_tab,also for actual partition add operation
           don't worry about the existed partition object,can get from user view partition path
           but now the new added partition path may like /dev/sda-1,not /dev/sda1
        '''
        self.disk=self.get_disk_from_path(part_disk_path)
        self.type=self.set_disk_partition_type(self.disk,part_type)
        self.free_part=self.disk.getFreeSpacePartitions()[0]
        self.geometry=self.set_disk_partition_geometry(self.disk,self.free_part,part_size)
        self.fs=parted.filesystem.FileSystem(part_fs,self.geometry,False,None)
        self.partition=parted.partition.Partition(self.disk,self.type,self.fs,self.geometry,None)

        return self.partition

        
    def add_disk_partition_info_tab(self,part_disk_path,part_type,part_size,part_fs,part_format,part_name,part_mountpoint):
        '''add partition to the table'''
        partition=self.get_disk_partition_object(part_disk_path,part_type,part_size,part_fs)
        if partition==None:
            print "partition is null"
            return 

        for item in self.disk_partition_info_tab:
            if partition.__eq__(item[0]):
                print "partition already added to the table"
                return 
        part_flag="add"   
        self.disk_partition_info_tab_item=[partition,part_disk_path,part_type,part_size,part_fs,
                                           part_format,part_name,part_mountpoint,part_flag]
        self.disk_partition_info_tab.append(self.disk_partition_info_tab_item)
        return self.disk_partition_info_tab

    def mark_disk_partition_info_tab(self,partition,part_flag):
        '''part_flag:keep,add,delete,according the flag to adjust the disk_partition_info_tab
           Then I can do partition add delete without bother the existed partition
        '''
        if(partition==None):
            print "partition doesn't exist"
            return
        for item in self.disk_partition_info_tab:
            if partition.__eq__(item[0]):# or partition.path==item[0].path:
                item[-1]=part_flag
        return  self.disk_partition_info_tab

    def delete_disk_partition_info_tab(self,partition):
        '''for origin partition,marked delete;for to added partition,rm from the table;'''
        if(partition==None):
            print "partition doesn't exist"
            return
        
        for item in self.disk_partition_info_tab:
            if partition.__eq__(item[0]): #or partition.path==item[0].path:
                if item[-1]=="add":
                    self.disk_partition_info_tab.remove(item)
                elif item[-1]=="keep":
                    self.mark_disk_partition_info_tab(partition,"delete")
                else:
                    print "invalid,if partition marked delete,you won't see it"
                    break
            else:
                continue

        return self.disk_partition_info_tab
#may not need this table
    def add_disk_partition_tab(self,disk,geometry,partition):
        '''add disk part tab,need consider handle except and part mount info'''
        disk_partition_tab_item=(disk,geometry,partition)
        try:
            self.disk_partition_tab.append(disk_partition_tab_item)
        except:
            print "add disk partition tab failed!"
        # return self.disk_partition_tab    


    def delete_disk_partition_tab(self,disk,partition):
        '''delete disk part tab item'''
        for disk_partition_tab_item in self.disk_partition_tab:
            if disk in disk_partition_tab_item and partition in disk_partition_tab_item:
                self.disk_partition_tab.remove(disk_partition_tab_item)
        else:
            print "the partition is not in the disk_partition_tab"
        # print self.disk_partition_tab            
                    
    def change_disk_partition_tab(self,disk,partition):
        pass


    #disk operations    
    def get_install_device_info(self):
        '''return dict {/dev/sda:size,/dev/sdb:size} to choose which to install linux deepin'''
        self.devices=parted.getAllDevices()
        self.install_info={}
        for device in self.devices:
            if "/dev/sd" in device.path or "/dev/hd" in self.device.path:
                dev_path=device.path
                dev_size=str(device.getSize(unit="GB"))+"GB"
                self.install_info[dev_path]=dev_size

        return self.install_info

    def get_system_disks(self):
        '''return list of system disks'''
        self.disks=[]
        self.devices=parted.getAllDevices()
        for device in self.devices:
            if "/dev/sd" in device.path or "/dev/hd" in self.device.path:
                self.disks.append(self.get_disk_from_path(device.path))
        return self.disks
        
    def get_disk_from_path(self,dev_path):
        '''from path:/dev/sda to get disk,need add except handle:/dev/sda1'''

        self.device=parted.device.Device(dev_path,None)
        try:
            self.disk=parted.disk.Disk(self.device,None)
        except:
            self.disk=self.set_disk_label(self.device)
        return self.disk    


    def get_device_from_path(self,dev_path):
        '''from path:/dev/sda to get device'''
        self.device=parted.device.Device(dev_path,None)
        return self.device

    def get_disk_size(self,disk):
        '''test function ,never used'''
        print disk.device.path+" disk size:"+ str(disk.device.getSize("GB")*1.0)+"GB"
       
        for part in self.get_disk_partitions(disk):
            print self.get_disk_partition_size(part)

    def set_disk_label(self,device):
        '''set disk label:gpt or msdos,to be extended'''
        
        if device.getSize() >= 1.5*1024*1024:
            self.disk=parted.freshDisk(device,"gpt")
        else:
            self.disk=parted.freshDisk(device,"msdos")
            
        return self.disk

    def recovery_disk_partitions(self,disk):
        pass


    def get_disk_partitions(self,disk):
        '''return partitions of the given disk'''
        self.partitions = []
        partition = disk.getFirstPartition()

        while partition:
            if partition.type & parted.PARTITION_FREESPACE or \
               partition.type & parted.PARTITION_METADATA or \
               partition.type & parted.PARTITION_PROTECTED:
                partition = partition.nextPartition()
                continue

            self.partitions.append(partition)
            partition = partition.nextPartition()

        return self.partitions

    #partition operations
    def get_disk_partition_size(self,partition):
        print partition.path+" partition size:"+str(partition.getSize("GB")*1.0)+"GB"

    def delete_disk_partition(self,disk,partition):
        '''atom function:delete the given partition,called only because need delete original partition'''
        self.partitions=self.get_disk_partitions(disk)
        if partition not in self.partitions:
            print "partition not in the disk"
            return

        if partition.type==parted.PARTITION_EXTENDED:
            if disk.getLogicalPartitions()!=[] :
                print "need delete all logical partitions before delete extend partition"
                return 

        disk.deletePartition(partition)
        disk.commitToDevice()

    def delete_custom_partition(self,partition_path):
        '''delete disk partition:get partition_path from ui
           This function can be called only because you want to delete the original partition
           umount it first
        '''
        for item in self.disk_partition_info_tab:
            if item[0].path==partition_path and item[-1]=="delete":
                self.partition=item[0]
                break
            else:
                continue
        if self.partition==None:
            print "partition doesn't exist"
            return
        self.disk=self.partition.disk

        self.delete_disk_partition(self.disk,self.partition)

    def recovery_disk_partition(self,disk,partition):
        pass

    def edit_disk_partition(self,disk,partition,info):
        '''edit partitiion size and file system,actually edit fs and geometry'''
        self.part_info=self.get_disk_partition_info(partition)
        self.part_size=partition.getSize()
        self.part_maxava_size=partition.getMaxAvailableSize(unit="MB")

    # def add_custom_partition(self,part_disk_path,part_type,part_size,part_fs,part_format,part_name,part_mountpoint):
    #     '''add partition according to customize'''

    #     self.disk=self.get_disk_from_path(part_disk_path)
    #     self.type=self.set_disk_partition_type(self.disk,part_type)
    #     self.free_part=self.disk.getFreeSpacePartitions()[0]
    #     self.geometry=self.set_disk_partition_geometry(self.disk,self.free_part,part_size)
    #     self.fs=parted.filesystem.FileSystem(part_fs,self.geometry,False,None)
    #     self.partition=self.add_disk_partition(self.disk,self.type,self.fs,self.geometry,None)
    #     self.set_disk_partition_fstype(self.partition,part_fs)
    #     self.set_disk_partition_name(self.partition,part_name)
    #     self.set_disk_partition_mount(self.partition,part_fs,part_mountpoint)

    def add_custom_partition(self,disk_partition_info_tab):
        '''add partition according to disk_partition_info_tab,then mount them'''
        for item in disk_partition_info_tab:
            if item[-1]=="add":
                self.partition=item[0]
                self.disk=self.partition.disk
                self.geometry=self.partition.geometry
                self.constraint=parted.constraint.Constraint(exactGeom=self.geometry)
                self.disk.addPartition(self.partition,self.constraint)
                self.part_fs=item[4]
                self.part_name=[6]
                self.part_mountpoint=[7]
                self.set_disk_partition_fstype(self.partition,self.part_fs)
                self.set_disk_partition_name(self.partition,self.part_name)
                self.disk.commit()
                self.set_disk_partition_mount(self.partition,self.part_fs,self.partition_mount)
                


    def set_disk_partition_type(self,disk,part_type):
        '''check the to added partition type,need consider the count of primary,extend,etc...'''
        if part_type=="primary":
            self.type=parted.PARTITION_NORMAL
        elif part_type=="extend":
            self.type=parted.PARTITION_EXTENDED
        elif part_type=="logical":
            self.type=parted.PARTITION_LOGICAL
        else:
            print "part type error"
        return self.type    

    def set_disk_partition_geometry(self,disk,free_part,size):
        '''return geometry of the to added partition,now just work for the first partition'''
        if free_part==None:
            free_part=disk.getFreeSpacePartitions()[0]
        #need to make sure the geometry.start of the new partition    
        self.start=free_part.geometry.start
        self.length=long(free_part.geometry.length*size/free_part.getSize())
        self.end=self.start+self.length-1
        if self.end > free_part.geometry.end:
            self.end=free_part.geometry.end
            self.length=self.end-self.start+1

        self.geometry=parted.geometry.Geometry(disk.device,self.start,self.length,self.end,None)
        return self.geometry
        
    def set_disk_partition_name(self,partition,part_name):
        '''cann't set this attribute,need to fix'''
        if part_name==None or len(part_name)==0:
            # print "don't need to set partition name"
            return

        if not partition.disk.supportsFeature(parted.DISK_TYPE_PARTITION_NAME):
            print "sorry,can't set partition name"
        else:
            partition.name=part_name
        
    # def add_disk_partition(self,disk,,geometry,PedPartition):
    #     '''create a partition to a given disk,need to consider the constraint'''
    #     # self.partition=self.get_disk_partition_object()

    #     self.constraint=parted.constraint.Constraint(exactGeom=self.geometry)
    #     disk.addPartition(self.partition,self.constraint)
    #     disk.commitToDevice()


    def set_disk_partition_fstype(self,partition,fstype):
        '''format the partition to given fstype,not create the parted fs object'''
        if partition.type!=parted.PARTITION_NORMAL and partition.type!=parted.PARTITION_LOGICAL:
            return
        if fstype==None or len(fstype)==0:
            return

        part_path=partition.path
        format_command="sudo mkfs -t "+fstype+part_path
        run_os_command(format_command)
    

    def set_disk_partition_mount(self,partition,fstype,mountpoint):
        '''mount partition to mp:new or modify,need consider various situation'''

        if partition.type==parted.PARTITION_EXTENDED:
            print "cann't mount extended partition"
            return
        if mountpoint==None or len(mountpoint)==0:
            print "need mountpoint,not given"
            return 

        part_path=partition.path
        mp=TARGET+mountpoint
        if not os.path.exists(mp):
            mkdir_command="sudo mkdir -p "+mp
            run_os_command(mkdir_command)
        if not os.path.exists(part_path):
            print "partition not exists,commit to os first"
            return 

        mount_command="sudo mount -t "+fstype+" "+part_path+" "+mp
        run_os_command(mount_command)
        
    def set_disk_partition_umount(self,partition):
        '''umount the partition,may used before remove a partition'''
        part_path=partition.path
        mount_flag=False
        mtab=get_os_command_output("cat /etc/mtab")
        umount_command="sudo umount "+part_path
        for item in mtab:
            if item.startswith(part_path):
                mount_flag=True

        if mount_flag==True:        
            if not partition.busy:
                run_os_command(umount_command)
            else:
                print "partition is busy,cann't umount"

    def get_disk_partition_mount(self,partition):
        '''get partition mount info,need consider multiple mount '''
        mountinfo=[]
        try:
            part_path=partition.path
            mtab=get_os_command_output("cat /etc/mtab")
            for item in mtab:
                if item.startswith(part_path):
                    mountinfo.append(item.split())
        except:
            print "cann't get mount info"
        return mountinfo        

    def set_disk_partition_flag(self,partition,flag,state):
        '''set the partition status to state'''
        if flag not in partition.getFlagsAsString():
            print "flag invalid"
        if not partition.isFlagAvailable():
            print "flag not available"
        else:    
            if state=="on" | state=="True":
                partition.setFlag()
            else:
                partition.unsetFlag()

def test1():
    #before add_disk_partition_info_tab and adjust the add_custom_partition function
    disk=PartUtil().get_disk_from_path("/dev/sda")
    pu=PartUtil()
    pu.add_custom_partition("/dev/sda","primary",2048,"ext4",None,None,"/")
    pu.add_custom_partition("/dev/sda","primary",2048,"ext4",None,None,"/home")
    pu.add_custom_partition("/dev/sda","extend",2048,"ext4",None,None,None)
    pu.add_custom_partition("/dev/sda","logical",1024,"ext4",None,None,None)
    print pu.disk_partition_tab

def test2():
    #test operate the disk_partition_info_tab
    print "origin"
    pu=PartUtil()
    for item in pu.init_disk_partition_info_tab():
        print item
    print "\n\n\n"
    print "add new partition"
    pu.add_disk_partition_info_tab("/dev/sda","primary",2048,"ext4",None,None,"/")
    pu.add_disk_partition_info_tab("/dev/sda","extend",4096,"ext4",None,None,"/")
    pu.add_disk_partition_info_tab("/dev/sda","logical",1024,"ext4",None,None,"/home")
    for item in pu.disk_partition_info_tab:
        print item
    print"\n\n\n"    
    p1=pu.get_disk_partition_object("/dev/sda","logical",1024,"ext4")
    print "delete new partition"
    pu.delete_disk_partition_info_tab(p1)
    print "\n\n\n"
    for item in pu.disk_partition_info_tab:
        print item
    print "\n\n\n"
    for item in pu.disk_partition_info_tab:
        if item[0].path=="/dev/sdb1":
            p2=item[0]
    print "delete exist partition"
    pu.delete_disk_partition_info_tab(p2)
    for item in pu.disk_partition_info_tab:
        print item

if __name__=="__main__":
    # pu=PartUtil()
    # pu.init_disk_partition_info_tab()
    # print "add new partition"
    # pu.add_disk_partition_info_tab("/dev/sda","primary",2048,"ext4",None,None,"/")
    # pu.add_disk_partition_info_tab("/dev/sda","extend",4096,"ext4",None,None,"/")
    # pu.add_disk_partition_info_tab("/dev/sda","logical",1024,"ext4",None,None,"/home")

    # print pu.refresh_disk_partition_info_tab(pu.disk_partition_info_tab)

    test2()
