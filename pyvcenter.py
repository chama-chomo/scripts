#!/usr/bin/env python3

from pyVim.connect import SmartConnect
import ssl
import re
import sys
from termcolor import colored, cprint
 
class Vcenter:
    '''connecting to hosts'''
    def __init__(self, vcenterhost, user='monvc', pwd='CiCt5.mon'):
        self.vcenterhost = vcenterhost
        self.user = user
        self.pwd = pwd
        self.s = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        self.s.verify_mode = ssl.CERT_NONE
        self.SConn = SmartConnect(host=self.vcenterhost, user=self.user, pwd=self.pwd, sslContext=self.s)
        self.at = (self.SConn.CurrentTime())
        print('''
        Connecting to: {}
                          (Actual Time: {})'''.format(self.vcenterhost, self.at))

    def DsUsage(self):
        try:
            datacenters = self.SConn.content.rootFolder.childEntity[0:]
        except: print('Could not connect to a Vcenter or gather object')

        for dc in datacenters:
            print('\n DATACENTER:', dc.name)
            dataSt = dc.datastore
            print(99 * '-')
            print('{:40} | {:10} | {:12} | {:12} | {:11} |'.format('Datastore name', 'Type', 'Free', 'Capacity', '% Free'))
            print(99 * '-')
            for dS in dataSt:
                ds_used_GB = int(dS.summary.capacity - dS.info.freeSpace / 1024 / 1024 / 1024)
                ds_free_GB = int(dS.info.freeSpace / 1024 / 1024 /1024)
                ds_sum_GB = int(dS.summary.capacity / 1024 /1024 /1024)
                ds_perc_free = int((ds_free_GB * 100) / ds_sum_GB)
                if ds_perc_free < 10:
                    blink_t = colored('Requires attention!!!', 'red', attrs=['blink'])
                    print('{:40} | {:10} | {:10}GB | {:10}GB | {:10}% | {}'.format(dS.name, dS.summary.type, ds_free_GB, ds_sum_GB, ds_perc_free, blink_t))
                else:
                    print('{:40} | {:10} | {:10}GB | {:10}GB | {:10}% |'.format(dS.name, dS.summary.type, ds_free_GB, ds_sum_GB, ds_perc_free))
            print(99 * '-')

    def RpUsage(self):
        try:
            datacenters = self.SConn.content.rootFolder.childEntity[0:]
        except: print('Could not connect to a Vcenter or gather object')

        for dc in datacenters:
            print('\n DATACENTER:', dc.name)
            hostF = dc.hostFolder.childEntity
            print(110 * '-')
            print('{:32} | {:20} | {:11} | {:22} | {:11} |'.format('RP name', 'CPU reserved/Limit', 'CPU Usage %', 'MEM reserved/Limit', 'MEM Usage %'))
            print(110 * '-')

            for respool in hostF:
                rPool = respool.resourcePool.resourcePool
                for rp in rPool:
                    #summary.config.cpuAllocation.reservation = cpu allocation - reservation Mhz
                    #staticCpuEntitlement = wors case allocation Mhz
                    #summary.config.memoryAllocation.limit = reservation aj limit MB
                    #staticMemoryEntitlement = worst case memory allocation MB
                    #summary.config.cpuAllocation.limit = cpu limit Mhz
                    #summary.runtime.cpu.overalUsage = ovarall cpu usage Mhz
                    cpuUsage_perc = int((rp.runtime.cpu.reservationUsed * 100) / rp.runtime.cpu.maxUsage)

                    rused_MB = int(rp.runtime.memory.reservationUsed /1024 / 1024)
                    mem_sum_MB = int(rp.runtime.memory.maxUsage / 1024 / 1024)
                    memUsage_perc_MB = int((rused_MB * 100 ) / mem_sum_MB)
                    cpu_f = " {} / {} ".format(rp.runtime.cpu.overallUsage, rp.runtime.cpu.maxUsage)
                    mem_f = " {} / {} ".format(rused_MB, mem_sum_MB)

                    print('{:32} | {:20} Mhz| {:11d}% | {:22} | {:11d}% |'.format(rp.name, cpu_f, cpuUsage_perc, mem_f, memUsage_perc_MB))

    def ListESXi(self):
        try:
            datacenters = self.SConn.content.rootFolder.childEntity[0:]
        except: print('Could not connect to a Vcenter or gather object')

        for dc in datacenters:
            print('\n DATACENTER:', dc.name)
            host_temp = dc.hostFolder.childEntity
            print(180 * '-')
            print('{:25} | {:14} | {:30} | {:44} | {:9} | {:5} | {:33} |'.format('ESXi host', 'Power State', 'HW model', 'CPU model', 'BIOS v.', 'TZ', 'Product'))
            print(180 * '-')

            for Rhost in host_temp:
                EHost = Rhost.host
                for esxih in EHost:
                    print('{:25} | {:14} | {:30} | {:44} | {:9} | {:5} | {:33} |'.format(esxih.name, esxih.runtime.powerState, esxih.summary.hardware.model, esxih.summary.hardware.cpuModel, esxih.hardware.biosInfo.biosVersion, esxih.config.dateTimeInfo.timeZone.name, esxih.config.product.fullName))

    def ListVMs(self):
        for dc in VC.connectvcenter():
            print('\n DATACENTER:', dc.name)
            vms = dc.vmFolder.childEntity
            for vm in vms:
                regex = re.search('vm-.*', str(vm))
                if regex is not None:
                    print('\n----------------------------------------------------------------------------')
                    if vm.guest.guestState == 'running':
                        print('VM:\033[1;31m {} \033[1;m'' [Status: \033[1;42m {} \033[1;m]'.format(vm.name, vm.guest.guestState))
                    elif vm.guest.guestState == 'notRunning':
                        print('VM:\033[1;31m {} \033[1;m'' [Status: \033[1;48m {} \033[1;m]'.format(vm.name, vm.guest.guestState))

                    dss = vm.datastore
                    print()
                    print('[[[\033[1;35mDATASTORES\033[1;m]]]')
                    for ds in dss:
                        print('> {}'.format(ds.name))

                    print('\n[[[\033[1;32mNETWORKS\033[1;m]]]')
                    print('IP: {}'.format(vm.guest.ipAddress))
                    nnet = vm.network
                    for net in nnet:
                        print('> {} '.format(net.name))

                    rrp = vm.resourcePool
                    print('\n[[[\033[1;36mRESOURCEPOOLS\033[1;m]]]')
                    if rrp is not None:
                        print('> {}    [RP_Parent:{}]'.format(rrp.name, rrp.parent.name))
                else:
                    break
     
    def ListVMsHtml(self):
        for dc in VC.connectvcenter():
            print('<table class="t2"><tr><th>DATACENTER:</th><td>{}</td></tr></table>'.format(dc.name))
            vms = dc.vmFolder.childEntity
            print('<table class="t1"')
            for vm in vms:
                regex = re.search('vm-.*', str(vm))
                if regex is not None:
                    if vm.guest.guestState == 'running':
                        print('<tr><th><br></th></tr><tr><th bgcolor="#B6B6B4">VM: [ {} ]</td><td colspan="3" bgcolor="#8BB381">[OS: {}] <pre>STATUS - {}<pre></td></tr>'.format(vm.name, vm.guest.guestFullName, vm.guest.guestState))
                    elif vm.guest.guestState == 'notRunning':
                        print('<tr><th><br></th></tr><tr><th bgcolor="#B6B6B4">VM: [ {} ]</td><td colspan="3" bgcolor="#E77471">[OS: {}] <pre>STATUS - {}</pre></td></tr>'.format(vm.name, vm.guest.guestFullName, vm.guest.guestState))

                    dss = vm.datastore
                    print('<tr><th colspan="2" bgcolor="#FFF8DC">DATASTORES</th></tr>')
                    for ds in dss:
                        print('<tr><td>{}</td></tr>'.format(ds.name))

                    print('<tr><th colspan="2" bgcolor="#FFF8DC">NETWORKS [IP: {}]</td></tr>'.format(vm.guest.ipAddress))
                    nnet = vm.network
                    for net in nnet:
                        print('<tr><td>{}</td></tr> '.format(net.name))

                    rrp = vm.resourcePool
                    print('<tr><th bgcolor="#FFF8DC">RESOURCEPOOLS</th><th bgcolor="#FFF8DC">RP Parent</th></tr>')
                    if rrp is not None:
                        print('<tr><td>{}</td><td>{}</td></tr>'.format(rrp.name, rrp.parent.name))

                    print('<tr><td><table class="usage"><th bgcolor="#E0FFFF">MEMORY ALLOC(MB)</th><th bgcolor="#E0FFFF">MEMORY RESERV(MB)</th><th bgcolor="#E0FFFF">CPU ALLOC</th><th bgcolor="#E0FFFF">CPU RESERV</th></tr>')
                    print('<tr><td >{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(vm.summary.config.memorySizeMB, vm.summary.config.memoryReservation, vm.runtime.maxCpuUsage, vm.summary.config.cpuReservation))
                    print('<tr><th bgcolor="#E0FFFF">MEM USAGE(MB)</th><th bgcolor="#E0FFFF">CPU USAGE(Mhz)</th><th bgcolor="#E0FFFF">SWAP MEM</th></tr>')
                    print('<tr><td>{}</td><td>{}</td><td>{}</td></table></td></tr>'.format(vm.summary.quickStats.guestMemoryUsage, vm.summary.quickStats.overallCpuUsage, vm.summary.quickStats.swappedMemory))
                else:
                    break
            else:
                break

    def printToHtml(self):
        sys.stdout = open('vcenter_vm_list.html', "wt")
        print("""<html>
        <head>
         <title>VCENTER's VM list</title>
        <style type="text/css">
        table.t1 {
            width: 80%
        }
        table.t1 td {
            text-align: right
        }
        table.t1 th {
            border: 0px solid black;
            text-align: left;
            padding: 2px
        }
        table.t2 td {
            border: 0px solid black;
            text-align: right
        }
        table.t2 th {
            border: 0px solid black
        }
        </style>
        </head>
        <body>
        """)

        print('<table class="t2"><tr><th>VCENTER</th><td>')
        print(self.vcenterhost, "</td></tr></table>")

        print (VC.ListVMsHtml())

        print("""</table>
        </body></html>""")


if __name__ == '__main__':

    VC = Vcenter('dsc01-vcper01.dscen.cz')
    #VC.printToHtml()
    #VC.DsUsage()
    VC.RpUsage()
    #VC.ListESXi()
