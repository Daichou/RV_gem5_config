Gem5 usage (RISC-V)
=========
### official tutorial
http://learning.gem5.org/book/index.html
https://www.gem5.org/documentation/
Because offical tutorial cover a lot content, so following tutorial focus on RISC-V and O3CPU.
### Installation
* install depenency
```shell
$ sudo apt install build-essential git m4 scons zlib1g zlib1g-dev libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev python-dev python automake
```
* get source code
```shell
$ git clone https://gem5.googlesource.com/public/gem5
```
* build gem5 (take long time to build)
```shell
$ cd gem5
$ scons build/RISCV/gem.opt -j8
```
### RISCV tools chain
* instal dependency
```shell
$ sudo apt-get install autoconf automake autotools-dev curl python3 libmpc-dev libmpfr-dev libgmp-dev gawk build-essential bison flex texinfo gperf libtool patchutils bc zlib1g-dev libexpat-dev
```
* get code
```shell
$ git clone --recursive https://github.com/riscv/riscv-gnu-toolchain
```
* Installation (riscv64-unknown-elf-gcc)
```shell
$ ./configure --prefix=/opt/riscv --with-arch=rv64ima --with-abi=lp64
$ make -j8
```
### Gem5 configuration
In configs folder:
```
.
├── boot
├── common
├── dist
├── dram
├── example
├── hpca_tutorials
├── network
├── ruby
├── splash2
├── topologies
└── tutorial
```
We can directly use config script in example folder to run full system CPU simulation.
```shell
$ ./build/RISCV/gem5.opt configs/example/se.py  --caches --cpu-type=DerivO3CPU -c tests/test-progs/hello/bin/riscv/linux/hello 
```
DeriveO3CPU must enable caches by --caches simultaneously.
`tests/test-progs` contains some prebuilt program.
DeriveO3CPU have some command line parameters which provided by python scripts in common folder,such as cache,memory. You can use --help to print out all of options. There are some useful options, such as cache configuration:
```
  --caches              
  --l2cache             
  --num-dirs=NUM_DIRS   
  --num-l2caches=NUM_L2CACHES
  --num-l3caches=NUM_L3CACHES
  --l1d_size=L1D_SIZE   
  --l1i_size=L1I_SIZE   
  --l2_size=L2_SIZE     
  --l3_size=L3_SIZE     
  --l1d_assoc=L1D_ASSOC
  --l1i_assoc=L1I_ASSOC
  --l2_assoc=L2_ASSOC   
  --l3_assoc=L3_ASSOC   
  --cacheline_size=CACHELINE_SIZE
    --list-hwp-types      List available hardware prefetcher types
  --l1i-hwp-type=L1I_HWP_TYPE
                                               type of hardware prefetcher to
                        use with the L1                       instruction
                        cache.                       (if not set, use the
                        default prefetcher of                       the
                        selected cache)
  --l1d-hwp-type=L1D_HWP_TYPE
                                               type of hardware prefetcher to
                        use with the L1                       data cache.
                        (if not set, use the default prefetcher of
                        the selected cache)
  --l2-hwp-type=L2_HWP_TYPE
                                               type of hardware prefetcher to
                        use with the L2 cache.                       (if not
                        set, use the default prefetcher of
                        the selected cache)
```
and branch predictors:
```
  --list-bp-types       List available branch predictor types
  --list-indirect-bp-types
                        List available indirect branch predictor types
  --bp-type=BP_TYPE                            type of branch predictor to run
                        with                       (if not set, use the
                        default branch predictor of                       the
                        selected CPU)
  --indirect-bp-type=INDIRECT_BP_TYPE
                        type of indirect branch predictor to run with

```
memory:
```
  --list-mem-types      List available memory types
  --mem-type=MEM_TYPE   type of memory to use
  --mem-channels=MEM_CHANNELS
                        number of memory channels
  --mem-ranks=MEM_RANKS
                        number of memory ranks per channel
  --mem-size=MEM_SIZE   Specify the physical memory size (single memory)
  --enable-dram-powerdown
                        Enable low-power states in DRAMCtrl
  --memchecker          
  --external-memory-system=EXTERNAL_MEMORY_SYSTEM
                        use external ports of this port_type for caches
  --tlm-memory=TLM_MEMORY
                        use external port for SystemC TLM cosimulation

```
However, those microarchitecture which insides CPU can not change by command line options. There are some way to change:

First way, change O3CPU source code. We only need to change "python" source code inside src/cpu/o3.
There are 2 file we can change:
##### `O3CPU.py`
```python
    activity = Param.Unsigned(0, "Initial count")

    cacheStorePorts = Param.Unsigned(200, "Cache Ports. "
          "Constrains stores only.")
    cacheLoadPorts = Param.Unsigned(200, "Cache Ports. "
          "Constrains loads only.")

    decodeToFetchDelay = Param.Cycles(1, "Decode to fetch delay")
    renameToFetchDelay = Param.Cycles(1 ,"Rename to fetch delay")
    iewToFetchDelay = Param.Cycles(1, "Issue/Execute/Writeback to fetch "
                                   "delay")
    commitToFetchDelay = Param.Cycles(1, "Commit to fetch delay")
    fetchWidth = Param.Unsigned(8, "Fetch width")
    fetchBufferSize = Param.Unsigned(64, "Fetch buffer size in bytes")
    fetchQueueSize = Param.Unsigned(32, "Fetch queue size in micro-ops "
                                    "per-thread")

    renameToDecodeDelay = Param.Cycles(1, "Rename to decode delay")
    iewToDecodeDelay = Param.Cycles(1, "Issue/Execute/Writeback to decode "
                                    "delay")
    commitToDecodeDelay = Param.Cycles(1, "Commit to decode delay")
    fetchToDecodeDelay = Param.Cycles(1, "Fetch to decode delay")
    decodeWidth = Param.Unsigned(8, "Decode width")
...
...
...
```
You can direct change those number in Param member function caller. But they have some limitation. For example, if you want to ramp up your issueWidth to 16, you must change MaxWidth in src/cpu/o3cpu/impl.hh:80 to 16, and you must assure your cacheline is bigger than 16*4 bytes.
WbWidth have some issue,it must larger than 4.
#### `FuncUnitConfig.py`
You can change function unit in execution stage by modifying this file.
`count` varible means the number of function unit.
`opLat` varible means the latency of this function unit.
`pipelined` varible is whether it is pipelined or not.

**After changing source code, you must use scons command to rebuild all project**
```shell
$ scons build/RISCV/gem.opt -j8
```

Second way is changing python object member value by assign in configuration file. Such as this file https://github.com/Daichou/RV_gem5_config/blob/master/config/se.py#L254.

### statistics analyse
After excuting simulation, gem5 will generate `m5out` folder.

You can read config.ini to make sure your configration as your expectation.

You can read stats.txt to check details performance number.

For O3CPU, there are some tools to visualize pipeline stage.
https://www.gem5.org/documentation/general_docs/cpu_models/visualization/

### Reference

* https://www.gem5.org/documentation/
* http://learning.gem5.org/tutorial/presentations/vis-o3-gem5.pdf
* https://github.com/shioyadan/Konata
* https://www.gem5.org/getting_started/
* https://www.gem5.org/events/asplos-2018
* http://learning.gem5.org
* https://www.cs.virginia.edu/~cr4bd/6354/F2016/homework2.html
* http://pages.cs.wisc.edu/~david/courses/cs752/Fall2015/gem5-tutorial/part1/simple_config.html
* http://www.m5sim.org/Running_gem5
* https://msyksphinz.hatenablog.com/entry/2018/12/04/040000
* https://carrv.github.io/2017/slides/roelke-risc5-carrv2017-slides.pdf
* https://gem5-users.gem5.narkive.com/c371fQ2w/how-to-change-the-issue-width-in-m5
* https://personal.utdallas.edu/~gxm112130/EE6304FA17/project2.pdf
* https://github.com/gem5/gem5/blob/master/src/cpu/o3/O3CPU.py
