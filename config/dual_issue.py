# Copyright (c) 2012-2013 ARM Limited
# All rights reserved.
#
# The license below extends only to copyright in the software and shall
# not be construed as granting a license to any other intellectual
# property including but not limited to intellectual property relating
# to a hardware implementation of the functionality of the software
# licensed hereunder.  You may use the software subject to the license
# terms below provided that you ensure that this notice is replicated
# unmodified and in its entirety in all distributions of the software,
# modified or unmodified, in source code or in binary form.
#
# Copyright (c) 2006-2008 The Regents of The University of Michigan
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Authors: Steve Reinhardt

# Simple test script
#
# "m5 test.py"
from __future__ import print_function
from __future__ import absolute_import

import optparse
import sys
import os

import m5
from m5.defines import buildEnv
from m5.objects import *
from m5.util import addToPath, fatal, warn
from m5.objects import BaseCache


from common import Options
from common import Simulation
from common import CacheConfig
from common import CpuConfig
from common import ObjectList
from common import MemConfig
from common.FileSystemConfig import config_filesystem
from common.Caches import *
from common.cpu2000 import *



def get_processes(options):
    """Interprets provided options and returns a list of processes"""

    multiprocesses = []
    inputs = []
    outputs = []
    errouts = []
    pargs = []

    workloads = options.cmd.split(';')
    if options.input != "":
        inputs = options.input.split(';')
    if options.output != "":
        outputs = options.output.split(';')
    if options.errout != "":
        errouts = options.errout.split(';')
    if options.options != "":
        pargs = options.options.split(';')

    idx = 0
    for wrkld in workloads:
        process = Process(pid = 100 + idx)
        process.executable = wrkld
        process.cwd = os.getcwd()

        if options.env:
            with open(options.env, 'r') as f:
                process.env = [line.rstrip() for line in f]

        if len(pargs) > idx:
            process.cmd = [wrkld] + pargs[idx].split()
        else:
            process.cmd = [wrkld]

        if len(inputs) > idx:
            process.input = inputs[idx]
        if len(outputs) > idx:
            process.output = outputs[idx]
        if len(errouts) > idx:
            process.errout = errouts[idx]

        multiprocesses.append(process)
        idx += 1

    if options.smt:
        assert(options.cpu_type == "DerivO3CPU")
        return multiprocesses, idx
    else:
        return multiprocesses, 1




class L1Cache(BaseCache):
    assoc = 4
    response_latency = 2
    tag_latency = 2
    mshrs = 4 # miss status handling register,to achieve noblocking cache
    tgts_per_mshr = 20
class L1ICache(L1Cache):
    size = '64kB'
    def connectCPU(self, cpu):
        self.cpu_side = cpu.icache_port
    def connectBus(self, bus):
        self.mem_side = bus.slave
    def connectMemSideBus(self, bus):
        self.mem_side = bus.slave

class L1DCache(L1Cache):
    size = '64kB'
    def connectCPU(self, cpu):
        self.cpu_side = cpu.dcache_port
    def connectBus(self, bus):
        self.mem_side = bus.slave
    def connectMemSideBus(self, bus):
        self.mem_side = bus.slave

parser = optparse.OptionParser()
Options.addCommonOptions(parser)
Options.addSEOptions(parser)


(options, args) = parser.parse_args()

if args:
    print("Error: script doesn't take any positional arguments")
    sys.exit(1)

multiprocesses = []
numThreads = 1

options.cpu_type = "DerivO3CPU"
multiprocesses, numThreads = get_processes(options)
(CPUClass, test_mem_mode, FutureClass) = Simulation.setCPUClass(options)
CPUClass.numThreads = numThreads

# np = options.num_cpus
np = 1
options.cacheline_size = 256
options.mem_size = '512MB'
options.sys_clock = '1MHz'
options.cpu_clock = '1MHz'

system = System(cpu = CPUClass(cpu_id = 0),
                mem_mode = 'timing',
                mem_ranges = [AddrRange(options.mem_size)],
                cache_line_size = options.cacheline_size)

if numThreads > 1:
    system.multi_thread = True

# Create a top-level voltage domain
system.voltage_domain = VoltageDomain(voltage = options.sys_voltage)

# Create a source clock for the system and set the clock period
system.clk_domain = SrcClockDomain(clock =  options.sys_clock,
                                   voltage_domain = system.voltage_domain)

# Create a CPU voltage domain
system.cpu_voltage_domain = VoltageDomain()

# Create a separate clock domain for the CPUs
system.cpu_clk_domain = SrcClockDomain(clock = options.cpu_clock,
                                       voltage_domain =
                                       system.cpu_voltage_domain)

# If elastic tracing is enabled, then configure the cpu and attach the elastic
# trace probe
if options.elastic_trace_en:
    CpuConfig.config_etrace(CPUClass, system.cpu, options)

# All cpus belong to a common cpu_clk_domain, therefore running at a common
# frequency.
for cpu in system.cpu:
    cpu.clk_domain = system.cpu_clk_domain

# Sanity check
if options.simpoint_profile:
    if not ObjectList.is_noncaching_cpu(CPUClass):
        fatal("SimPoint/BPProbe should be done with an atomic cpu")
    if np > 1:
        fatal("SimPoint generation not supported with more than one CPUs")

system.cpu[0].workload = multiprocesses

if options.simpoint_profile:
    system.cpu[0].addSimPointProbe(options.simpoint_interval)

if options.checker:
    system.cpu[0].addCheckerCpu()

if options.bp_type:
    bpClass = ObjectList.bp_list.get(options.bp_type)
    system.cpu[0].branchPred = bpClass()

if options.indirect_bp_type:
    indirectBPClass = \
        ObjectList.indirect_bp_list.get(options.indirect_bp_type)
    system.cpu[0].branchPred.indirectBranchPred = indirectBPClass()

system.cpu[0].createThreads()

l1icache = L1ICache()
l1dcache = L1DCache()

#CacheConfig.config_cache(options, system)
#MemConfig.config_mem(options, system)
config_filesystem(system, options)
MemClass = Simulation.setMemClass(options)
system.cpu[0].addPrivateSplitL1Caches(l1icache,l1dcache)
#system.cpu[0].icache = L1ICache()
#system.cpu[0].dcache = L1DCache()
#system.cpu[0].icache.connectCPU(system.cpu[0])
#system.cpu[0].dcache.connectBus(system.cpu[0])
#system.cpu[0].icache.connectMemSideBus(system.membus)
#system.cpu[0].dcache.connectMemSideBus(system.membus)

system.membus = CoherentXBar()
# Connect the system up to the membus
system.system_port = system.membus.slave

# Create a DDR3 memory controller
system.mem_ctrl = DDR3_1600_8x8()
system.mem_ctrl.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.master
system.cpu[0].connectAllPorts(system.membus)
#system.cpu[0].createInterruptController()
#system.cpu[0].interrupts[0].pio = system.membus.master
#system.cpu[0].interrupts[0].int_master = system.membus.slave
#system.cpu[0].interrupts[0].int_slave = system.membus.master
#system.system_port = system.membus.slave
system.cpu[0].createInterruptController()

system.cpu[0].fetchWidth=2
system.cpu[0].issueWidth=2
system.cpu[0].dispatchWidth=2
system.cpu[0].decodeWidth=2
system.cpu[0].commitWidth=2
system.cpu[0].renameWidth=2
system.cpu[0].wbWidth=4
system.cpu[0].squashWidth=2
system.cpu[0].commitToIEWDelay=2

root = Root(full_system = False, system = system)
Simulation.run(options, root, system, FutureClass)

