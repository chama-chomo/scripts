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
        print('-' * 91 )
        print('| {:15} | {:30} | {:20} | {:13} |'.format('Cluster Name', 'ESXi host', 'Status', 'Uptime[days]'))
       
        for child in self.children:
            print('-' * 91 )
            chname = child.name
            chstatus = child.summary.overallStatus
            print('| {:15} | {:30} | {:20} |'.format(chname, ' ', chstatus))

            for host in child.host:
                hName = host.name
                hStatus = host.summary.overallStatus
                hUptime = host.summary.quickStats.uptime / 86400
                print('| {:15} | {:30} | {:20} | {:13.1f} |'.format('', hName, hStatus, hUptime))
        print('-' * 91 )

    def getClusterInfo(self, clName):
        for child in self.children:
            if child.name == clName:
                clName = child.name
                clStatus = child.summary.overallStatus
                print('\nCluster: {:15} - status: {:10}'.format(clName, clStatus))

                for host in child.host:
                    hName = host.name
                    hStatus = host.summary.overallStatus
                    print('--- ESXi Host: {:20} - status: {:10}'.format(hName, hStatus))
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
        print('-' * 152 )
        print('| {:45} | {:15} | {:24} | {:55} |'.format('VM name', 'State', 'IP address', 'Guest OS'))
        print('-' * 152 )
        for child in self.children:
            if child.summary.guest is not None:
                name = child.name
                isgRunning = child.guest.guestState
                power = child.summary.runtime.powerState
                system = child.summary.config.guestFullName
                ip = '{}'.format(child.guest.ipAddress)
                print('| {:45} | {:15} | {:24} | {:55} |'.format(name, isgRunning, ip, system))

    def showVMInfo(self, vmName):
        for child in self.children:
            regex_s = re.match(r'(.*{}.*)'.format(vmName), child.name, re.IGNORECASE)

            if regex_s is not None:
                name = child.name
                ip = '{}'.format(child.guest.ipAddress)
                OsFullName = child.summary.config.guestFullName
                memSize = child.summary.config.memorySizeMB
                cpuCount = child.summary.config.numCpu
                ethCount = child.summary.config.numEthernetCards
                hostName = child.summary.guest.hostName

                print('Match "{}" for regex string "{}"'.format(child.name, vmName))
                print('''
                VM Name: {}
                Hostname: {}
                OS type: {}
                IP Address: {}
                CPU count / Memory size(MB)- {} / {}
                Network devices count: {}
                '''.format(name, hostName, OsFullName, ip, cpuCount, memSize, ethCount))
                for net in child.network:
                    print('Network connected: {}'.format(net.name))
                for ds in child.datastore:
                    print('Datastore used: {}'.format(ds.name))
                # for rp in child.resourcePool.resoucePool:
                #     print('ResourcePool assigned: {}'.format(rp.name))
                print('ResourcePool assigned: {}'.format(child.resourcePool.name))
                print('-' * 152 )
            else:
                pass

class dataStores:
    def __init__(self, si, dsName=None):
            self.si = si
            self.dsName = dsName

            content = self.si.RetrieveContent() # starting point
            container = content.rootFolder # get rootFolder
            recursive = True
            viewType = [vim.Datastore]
            containerView = content.viewManager.CreateContainerView(container,
                                                                    viewType,
                                                                    recursive) # Create a view
            self.children = containerView.view

    def listDatastores(self):
        print('-' * 83)
        print('| {:35} | {:10} | {:15} | {:10} |'.format('Datastore name', 'Type', 'Capacity[GB]', 'Free %'))
        print('-' * 83)

        for child in self.children:
            dsName = child.name
            dsCapacity = child.summary.capacity / 1024 / 1024 / 1024
            dsFreeSpace_perc = int((child.summary.freeSpace * 100) / (child.summary.capacity +1))
            dsType = child.summary.type
            dsStatus = child.summary.accessible

            if dsStatus is not True:
                print('| {:35} | {:10} | {:15} | {:10} |'.format(dsName, dsType, 'inaccessible', 'n/a'))
            else:
                print('| {:35} | {:10} | {:15.0f} | {:10} |'.format(dsName, dsType, dsCapacity, dsFreeSpace_perc))

        print('-' * 83)

    def listDatastoresFull(self):
        print('-' * 83)
        print('INFO: Printing only Datastores with less than 11% free space')
        print('| {:35} | {:10} | {:15} | {:10} |'.format('Datastore name', 'Type', 'Capacity[GB]', 'Free %'))
        print('-' * 83)

        for child in self.children:
            dsName = child.name
            dsCapacity = child.summary.capacity / 1024 / 1024 / 1024
            dsFreeSpace_perc = int((child.summary.freeSpace * 100) / (child.summary.capacity +1))
            dsType = child.summary.type
            dsStatus = child.summary.accessible

            if dsStatus is not True:
                print('| {:35} | {:10} | {:15} | {:10} |'.format(dsName, dsType, 'inaccessible', 'n/a'))
            else:
                if dsFreeSpace_perc < 11:
                    print('| {:35} | {:10} | {:15.0f} | {:10} |'.format(dsName, dsType, dsCapacity, dsFreeSpace_perc))

        print('-' * 83)


    def usedByDatastores(self):
            print('-' * 83)
            print('| {:35} | {:30} | {:50} | {:7} |'.format('Datastore name', 'Used by Hosts', 'Used by VMs', 'Free %'))
            print('-' * 83)

            for child in self.children:
                dsName = child.name
                dsFreeSpace_perc = int((child.summary.freeSpace * 100) / (child.summary.capacity +1))
                dsStatus = child.summary.accessible
                dsUsedVms = child.vm[0:]
                dsUsedHosts = child.host#[0:]
                vmList = []
                hostList = [] 
                for vm in dsUsedVms:
                    vmList.append(vm)

                for host in dsUsedHosts:
                    hostList.append(host)

                v = (vmList)
                h = (hostList)

                vmList_n = []
                for vmm in v:
                   vmList_n.append(vmm.name)

                s = str(vmList_n)

                hostList_n = [] 
                for hosth in h:
                    hostList_n.append(hosth.key.name)

                h = str(hostList_n)

                dsName_c = colored('Datastore name:', 'red')
                vmServed_c = colored('VMs served:', 'red')
                hostServed_c = colored('Hosts served:', 'red')
                dsName_cc = colored(dsName, 'yellow')
                dsName_na = colored(dsName, 'red')


                if dsStatus is not True:
                    print('-' * 150)
                    print('{:30} {} - Not accessible'.format(dsName_c, dsName_na))
                else:
                    print('-' * 150)
                    print('{:30} {}'.format(dsName_c, dsName_cc))
                    print('\n{:30} {}'.format(vmServed_c, s))
                    print('{:30} {}'.format(hostServed_c, h))
                   


class esxiHosts:
    def __init__(self, si, esxiName=None):
        self.si = si
        self.esxiName = esxiName

        content = self.si.RetrieveContent() # starting point
        container = content.rootFolder # get rootFolder
        recursive = True
        viewType = [vim.HostSystem]
        containerView = content.viewManager.CreateContainerView(container,
                                                                viewType,
                                                                recursive) # Create a view
        self.children = containerView.view

    def listHosts(self):
        print('-' * 157)
        print('| {:25} | {:35} | {:6} | {:6} | {:25} | {:20} | {:10} | {:5} |'.format('Host Name', 'Model', 'CPU%', 'MEM%', 'VMWare ver.', 'Bios', 'FW', 'TZ'))
        print('-' * 157)
       
        for child in self.children:
            hostName = child.name
            hostModel = child.hardware.systemInfo.model
            hostBiosInfo = child.hardware.biosInfo.biosVersion
            hostFwRel = '{}.{}'.format(child.hardware.biosInfo.firmwareMajorRelease, child.hardware.biosInfo.firmwareMinorRelease)
            vmwareInstalled = '{}-{}'.format(child.config.product.version, child.config.product.build)
            hostTz = child.config.dateTimeInfo.timeZone.name
            cpuUsage_perc = int((child.summary.quickStats.overallCpuUsage * 100) / child.systemResources.config.cpuAllocation.limit)
            memUsage_perc = int((child.summary.quickStats.overallMemoryUsage * 100) / child.systemResources.config.memoryAllocation.limit)
            print('| {:25} | {:35} | {:6} | {:6} | {:25} | {:20} | {:10} | {:5} |'.format(hostName,
                                                                                          hostModel,
                                                                                          cpuUsage_perc,
                                                                                          memUsage_perc,
                                                                                          vmwareInstalled,
                                                                                          hostBiosInfo,
                                                                                          hostFwRel,
                                                                                          hostTz))

        print('-' * 157)

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
                rpName = child.name
                rpStatus = child.overallStatus
                print('| {:35} | {:35} | {:10} |'.format(rpName, ' ', rpStatus))

                for uResPool in child.resourcePool:
                    urpName = uResPool.name
                    urpStatus = uResPool.overallStatus
                    if uResPool.resourcePool == []:
                        print('| {:35} | {:35} | {:10} |'.format(' ', urpName, urpStatus))
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
        print('-' * 91)
        print('| {:35} | {:36} | {:10} |'.format('Datacenter name', 'Serviced domains', 'Status'))

        for child in self.children:
            dcName = child.name
            dcStatus = child.overallStatus
            print('-' * 91)
            print('| {:35} | {:36} | {:10} |'.format(dcName, '', dcStatus))
            for dcEnt in child.hostFolder.childEntity:
                hName = dcEnt.name
                hStatus = dcEnt.overallStatus
                print('| {:35} | {:36} | {:10} |'.format('', hName, hStatus))
        print('-' * 91)
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
       [4] dsc02-vcper01.dscen.cz''')
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
        vcenterInstance = {'dsc02-vcper01.dscen.cz'}

    print("\033c")
    for instance in vcenterInstance:
        vc = vCenter(instance) 
        serviceInstance = vc.vCenterConnect()
        vc.vCenterList(serviceInstance)

    print('''\nAvailable queries are:
    ===============================================================
    [1]      Clusters (default: List all)
    [11]     Get specific Cluster information
    ===============================================================
    [2]      List Virtual Machines (default: List all )
    [21]     Show specifc VM info  (search based on regex provided)
    ===============================================================
    [3]      List Resource Pools(default: List all)
    ===============================================================
    [4]      List Datacenters(default: List all)
    ===============================================================
    [5]      List Datastores(default: List all)
    [51]     Objects using Datastores
    [52]     List Datastores reaching full usage
    ===============================================================
    [6]      List ESXi Hosts (default: List all)
    ===============================================================''')
    querySelect = int(input('Select Query: '))

    if querySelect == 21:
            vmName = input('\nType a VM name (the one in the VCenter) or regex string that will be used to match the VM name: ')

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
        if querySelect == 21:
            object = VirtualMachines(serviceInstance)
            object.showVMInfo(vmName)
        if querySelect == 3:
            object = resourcePool(serviceInstance)
            object.listResourcePools()
        if querySelect == 4:
            object = dataCenters(serviceInstance)
            object.listDatacenters()
        if querySelect == 5:
            object = dataStores(serviceInstance)
            object.listDatastores()
        if querySelect == 51:
            object = dataStores(serviceInstance)
            object.usedByDatastores()
        if querySelect == 52:
            object = dataStores(serviceInstance)
            object.listDatastoresFull()
        if querySelect == 6:
            object = esxiHosts(serviceInstance)
            object.listHosts()


    


