#!/usr/bin/env python3

from pyVim.connect import SmartConnect
from pyVim import connect
from pyVmomi import vim
import ssl
import re
import sys
import atexit
from termcolor import colored, cprint


class vCenter:
    '''Defines VCENTER'''
    def __init__(self, vcHost, user='monvc', pwd='CiCt5.mon'):
        self.vcHost = vcHost
        self.user = user
        self.pwd = pwd

    def vCenterConnect(self):
        '''Connecting to Vcenter'''
        sslProt =  ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        sslProt.verify_mode = ssl.CERT_NONE
        try:
            serviceInstance = SmartConnect(host=self.vcHost, user=self.user, pwd=self.pwd, sslContext=sslProt)
        except IOError:
            print('Could not connect to VCENTER: {} with user {}'.format(self.vcHost, self.user))

        atexit.register(connect.Disconnect, serviceInstance) 

        return serviceInstance

    def vCenterList(self, si):
        '''Vcenter status'''
        if not si:
            raise SystemExit('Unable to connect to VCENTER with supplied info.')
        else:
            vCenterTime = (si.CurrentTime())
            print('Connected to {} with the actual time: {}'.format(self.vcHost, vCenterTime))

class Clusters():
    def __init__(self, si, clName=None):
        self.si = si
        self.clName = clName

        content = self.si.RetrieveContent() # starting point
        container = content.rootFolder # get rootFolder
        recursive = True
        viewType = [vim.ClusterComputeResource]
        containerView = content.viewManager.CreateContainerView(container,
                                                                viewType,
                                                                recursive) # Create a view
        self.children = containerView.view

    def listClusters(self):
        print('-' * 88 )
        print('| {:15} | {:30} | {:20} | {:13} |'.format('Cluster Name', 'ESXi host', 'Status', 'Uptime[days]'))
       
        for child in self.children:
            print('-' * 88 )
            chname = child.name
            chstatus = child.summary.overallStatus
            print('| {:15} | {:30} | {:20} |'.format(chname, '', chstatus))
            for host in child.host:
                hname = host.name
                hstatus = host.summary.overallStatus
                huptime = host.summary.quickStats.uptime / 86400
                print('| {:15} | {:30} | {:20} | {:13.1f} |'.format('', hname, hstatus, huptime))

        print('-' * 88 )

    def getClusterInfo(self, clName):
        for child in self.children:
            if child.name == clName:
                print('\nCluster: {:15} - status: {:10}'.format(child.name, child.summary.overallStatus))
                for host in child.host:
                    print('--- ESXi Host: {:20} - status: {:10}'.format(host.name, host.summary.overallStatus))
                cpu_perc = int((child.summary.usageSummary.cpuDemandMhz * 100) / child.summary.totalCpu)
                print('Consumed Cluster CPU: {}%'.format(cpu_perc))

class VirtualMachines():
    def __init__(self, si):

        self.si = si
        
        content = self.si.RetrieveContent() # starting point
        container = content.rootFolder # get rootFolder
        recursive = True
        viewType = [vim.VirtualMachine]
        containerView = content.viewManager.CreateContainerView(container,
                                                                viewType,
                                                                recursive) # Create a view
        self.children = containerView.view


    def listVMs(self):
        print('-' * 132 )
        print('| {:45} | {:15} | {:14} | {:45} |'.format('VM name', 'IP address', 'State', 'Guest OS'))
        print('-' * 132 )
        for child in self.children:
            if child.summary.guest is not None:
                name = child.name
                isgRunning = child.guest.guestState
                power = child.summary.runtime.powerState
                system = child.summary.config.guestFullName
                ip = '{}'.format(child.guest.ipAddress)
                print('| {:45} | {:15} | {:14} | {:45} |'.format(name, isgRunning, ip, system))


class dataStores:
    pass

class esxiHosts:
    pass

class resourcePool:
    def __init__(self, si, rpName=None):
        self.si = si
        self.rpName = rpName

        content = self.si.RetrieveContent() # starting point
        container = content.rootFolder # get rootFolder
        recursive = True
        viewType = [vim.ResourcePool]
        containerView = content.viewManager.CreateContainerView(container,
                                                                viewType,
                                                                recursive) # Create a view
        self.children = containerView.view

    def listResourcePools(self):
        print('-' * 90)
        print('| {:35} | {:36}| {:10} |'.format('ResourcePool name', 'Child RP name', 'Status'))
        for child in self.children:
            if child.name == 'Resources':
                pass
            elif child.parent.name == 'Resources':
                print('-' * 90)
                print('| {:35} | {:35} | {:10} |'.format(child.name, ' ', child.overallStatus))
                for uResPool in child.resourcePool:
                    if uResPool.resourcePool == []:
                        print('| {:35} | {:35} | {:10} |'.format(' ', uResPool.name, uResPool.overallStatus))

        print('-' * 90)

class dataCenters:
    def __init__(self, si, dcName=None):
        self.si = si
        self.dcName = dcName

        content = self.si.RetrieveContent() # starting point
        container = content.rootFolder # get rootFolder
        recursive = True
        viewType = [vim.Datacenter]
        containerView = content.viewManager.CreateContainerView(container,
                                                                viewType,
                                                                recursive) # Create a view
        self.children = containerView.view

    def listDatacenters(self):
        
        for child in self.children:
            print('\nDatacenter: {:35} - status: {:10}'.format(child.name, child.overallStatus))
            for dcEnt in child.hostFolder.childEntity:
                print('--- Serving domains: {:35} - status {:10}'.format(dcEnt.name, dcEnt.overallStatus))

##################################################################################
##################################################################################
##################################################################################

if __name__ == '__main__':
    print("\033c")
    print('''Available vcenter instances are:
       [0] Query all available instances from list below
       [1] dsc01-vcvsp01.dscen.cz
       [2] dsc01-vcper01.dscen.cz
       [3] dsc02-vcvsp01.dscen.cz
       [4] dsc01-vcper01.dscen.cz''')
    vcenterSelect = int(input('Choose instance: '))
    if vcenterSelect == 0:
        vcenterInstance = ['dsc01-vcvsp01.dscen.cz', 'dsc01-vcper01.dscen.cz', 'dsc02-vcvsp01.dscen.cz', 'dsc02-vcper01.dscen.cz']
    if vcenterSelect == 1:
        vcenterInstance = ['dsc01-vcvsp01.dscen.cz']
    if vcenterSelect == 2:
        vcenterInstance = ['dsc01-vcper01.dscen.cz']
    if vcenterSelect == 3:
        vcenterInstance = ['dsc02-vcvsp01.dscen.cz']
    if vcenterSelect == 4:
        vcenterInstance = {'dsc02-vcvsp01.dscen.cz'}

    print("\033c")
    for instance in vcenterInstance:
        vc = vCenter(instance) 
        serviceInstance = vc.vCenterConnect()
        vc.vCenterList(serviceInstance)

    print('''\nAvailable queries are:
    [1] List Clusters
    [11] Get specific Cluster information
    [2] List Virtual Machines
    [3] List Resource Pools
    [4] List Datacenters''')
    querySelect = int(input('Choose instance: '))

    print("\033c")
    for instance in vcenterInstance:
        print('\n')
        print('-' * 60)
        print(' Retrieving data for instance: {:60} '.format(instance))
        print('-' * 60)
        vc = vCenter(instance) 
        serviceInstance = vc.vCenterConnect()

        if querySelect == 1:
            object = Clusters(serviceInstance)
            object.listClusters()
        if querySelect == 11:
            object = Clusters(serviceInstance)
            inp = input('Type a Cluster name: ')
            object.getClusterInfo(inp)
        if querySelect == 2:
            object = VirtualMachines(serviceInstance)
            object.listVMs()
        if querySelect == 3:
            object = resourcePool(serviceInstance)
            object.listResourcePools()
        if querySelect == 4:
            object = dataCenters(serviceInstance)
            object.listDatacenters()


    


