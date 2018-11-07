#!/usr/bin/env python3
import atexit
import argparse
import sys
import os
import time
import ssl

from pyVmomi import vim, vmodl
from pyVim import connect
from pyVim.connect import Disconnect, SmartConnect


os.system('clear') 
print('-' * 100)
print('This tool contacts VCENTER via its API and modifies networking parameters for the specified VM. Please use it carefully!')
print('VM to be modified should be turned off before running the script')
print('-' * 100)

print('''Possibilities for the below input are:
dsc01-vcvsp01.dscen.cz  dsc01-vcper01.dscen.cz  dsc02-vcvsp01.dscen.cz  dsc02-vcper01.dscen.cz''')
vcenter_ip = input('\nProvide Vcenter name on which VM is configured: ')
print('\nYour Vcenter user (DSCEN Domain name will be automatically included)')
vcenter_user_ask = input('Provide Vcenter user: ')
vcenter_user = 'DSCEN\{}'.format(vcenter_user_ask)
vcenter_password = input('Provide password for the user {} :'.format(vcenter_user))
vm_name = input('Provide a VM name (as named in the VCENTER: ')
hostName = input('What will be the hostname of the VM: ')
isDHCP = False
vm_ip = input('Provide the IP of the VM: ')
subnet = input('Provide the subnet mask in x.x.x.x format (if empty default /24 will be used): ')
if not subnet:
    subnet = '255.255.255.0'
gateway = input('Provide the IP of a Gateway: ')
#dns = ['11.110.135.51', '11.110.135.52']
domain = input('What will be the domain used: ')
os.system('clear') 

print('Following Inputs have been provided, please check them carefully and confirm by pressing ENTER or cancel by pressing Ctrl-C')
print('-' * 100)
print('VCENTER IP: {}'.format(vcenter_ip))
print('VCENTER USER: {}'.format(vcenter_user))
if vcenter_password is not None:
    print('VCENTER PASSWORD: set, not shown')
print('-' * 100)
print('VM NAME: {}'.format(vm_name))
print(' HOSTNAME: {}'.format(hostName))
print(' VM IP: {}'.format(vm_ip))
print(' SUBNET: {}'.format(subnet))
print(' GATEWAY: {}'.format(gateway))
print(' DOMAIN: {}'.format(domain))
print('-' * 100)
input('confirm by pressing ENTER or cancel by pressing Ctrl-C')

def get_obj(content, vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """    
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

def wait_for_task(task, actionName='job', hideResult=False):
    """
    Waits and provides updates on a vSphere task
    """
    print('Waiting phase..')
    
    while task.info.state == vim.TaskInfo.State.running:
        time.sleep(2)
    
    if task.info.state == vim.TaskInfo.State.success:
        if task.info.result is not None and not hideResult:
            out = '{} completed successfully, result: {}'.format(actionName, task.info.result)
            print(out)
        else:
            out = '{} completed successfully.'.format(actionName)
            print(out)
    elif task.info.state == vim.TaskInfo.State.queued:
        print('This task has been queued, start your VM to finish the task')
    elif task.info.state == vim.TaskInfo.State.running:
        print('This task is still running, start your VM to finish the task')
    else:
        out = '{} did not complete successfully: {}'.format(actionName, task.info.error)
        #raise task.info.error
        print(out)
    
    return task.info.result

def main():
    #args = GetArgs()
    sslProt =  ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    sslProt.verify_mode = ssl.CERT_NONE

    si = None
    try:
        print("Trying to connect to VCENTER SERVER . . .")
        si = SmartConnect(host=inputs['vcenter_ip'], user=inputs['vcenter_user'], pwd=inputs['vcenter_password'], sslContext=sslProt)

    except IOError:
        pass
        atexit.register(Disconnect, si)

    print("Connected to VCENTER SERVER !")

    content = si.RetrieveContent()

    #vm_name = args.vm
    vm_name = inputs['vm_name']      
    vm = get_obj(content, [vim.VirtualMachine], vm_name)

    if vm.runtime.powerState != 'poweredOff':
        print("WARNING:: Power off your VM before reconfigure")
        sys.exit()

    adaptermap = vim.vm.customization.AdapterMapping()
    globalip = vim.vm.customization.GlobalIPSettings()
    adaptermap.adapter = vim.vm.customization.IPSettings()

    isDHDCP = inputs['isDHCP']
    if not isDHDCP:
        """Static IP Configuration"""
        adaptermap.adapter.ip = vim.vm.customization.FixedIp()
        adaptermap.adapter.ip.ipAddress = inputs['vm_ip']
        adaptermap.adapter.subnetMask = inputs['subnet']
        adaptermap.adapter.gateway = inputs['gateway']  
        #globalip.dnsServerList = inputs['dns']

    # else:
    #     """DHCP Configuration"""
    #     adaptermap.adapter.ip = vim.vm.customization.DhcpIpGenerator()

    adaptermap.adapter.dnsDomain = inputs['domain']

    globalip = vim.vm.customization.GlobalIPSettings()

    #For Linux . For windows follow sysprep
    ident = vim.vm.customization.LinuxPrep(domain=inputs['domain'], hostName=vim.vm.customization.FixedName(name=inputs['hostName']))        

    customspec = vim.vm.customization.Specification()
    #For only one adapter
    customspec.identity = ident
    customspec.nicSettingMap = [adaptermap]
    customspec.globalIPSettings = globalip

    #Configuring network for a single NIC
    #For multipple NIC configuration contact me.

    print("Reconfiguring VM Networks . . .")

    task = vm.Customize(spec=customspec)

    # Wait for Network Reconfigure to complete
    wait_for_task(task, si)        

    # except vmodl.MethodFault:
    #     print("Caught vmodl fault: %s" % msg)
    #     return 1
    # except Exception:
    #  print("Caught exception")
    #  return 1
    
# Start program
if __name__ == '__main__':
    main()
