# LLAC (Low Latency Audio Core dynamic allocator, platform & architecture for FPGA's)

LLAC started as a research project for low-latency user defined audio cores. It targets the AMD [Xilinx](https://github.com/xilinx) platform, specifically the [PYNQ](https://github.com/Xilinx/PYNQ) platform. The project has the following goals:

1. **Allow for highly parallel** FX, synthesis, mixing, filtering etc... possibilities that exploit superior multi-channel proccessing capabilities offered by FPGA's
2. **Minimise latency** as much as possible
3. **Replicate modern audio synthesis hardware as much as possible** (specifically, in regard to the fact that both latency & the simulated behaviour of circuits should be as close to their hardware siblings as possible, just in the form of a low-level RTL system rather than an ASIC)
4. **Allow for extensible IO options**
5. **Allow for the platform to be user-configurable** in a way not offered by ASIC platforms

These goals are perfectly suited in-line with an FPGA platform; hence the impetus for the project.

## FPGA based system architecture overview

Because the aforementioned goals have such good synergy & parity with an FPGA based design, the broad-level hardware system architecture includes the following:

___
### _Static_ hardware elements
> Of course, every part of the fabric has to be dynamic. It might be that a element / component should never have a reason to be touched by partial reconfiguration because it would break the processing chain. 

> Typically either:
> * Frequently called elements
> * Necessary / expected elements
> * Elements that are critical to the processing chain's latency or cause artefacts when removed
> * Highly optimised or pipelined elements (I.e. in much the same way that a hot-path might have hand-rolled assembly)
> * Elements that significantly interleave common user functions, AXI, communication protocols, IO protocols or are otherwise very in-situ because of their constant reporting
> * Expensive, or otherwise makes little to no sense, for the component to be reconfigurable

> [!NOTE]
> Examples include: two-pole / second order filters, buses, typical IP cores, common user functions like FFT, common user FX 'banks' like Delay, reverb Etc.

___

___
### _Connections_ (Buses, 'Routing matrices', Pipes, AXI etc...)

> [Audio ensemble cores](#audio-ensemble-cores) need to communicate with each other, the off-FPGA infrastructure (_I.e. See: [Zynq Z-2 docs](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/695/DFR0600_Web.pdf)_ & additionally need to frequently report their status or have their state piped into other elements or access shared pools of memory like when doing sampling or granular synthesis.

> [!NOTE]
> There is some notable overlap here with _Deferred analysis_. That is, elements that are used in connective paths are not mutually exclusive with other elements, particularly those that have a role in deciding the footprint of the fabric. The routing matrix, for instance, is a state based input into the [allocator algorithms](#software--allocator-based-system-architecture-overview)
___

___
### Audio _ensemble cores_

> Audio ensemble cores are the partially reconfigurable 'crux' of the project components that allow the user to combine on-fabric logic & off-fabric software based implementations into a multi-channel truly parallel effects processing environment. They are essentially the 'modules' that are slotted into by the user to allow for the experience of virtualized, swappable hardware. Kind of like if you could write multiple of your own hard-synthesizers in code and have them run in parallel.

___
### _Deferred analysis_ components

> These are components that collect metrics or information about the system as it runs. For instance, one of the most essential metrics is how many times (how frequently) a user-defined module calls each other relevant module so that the Allocator can intelligently decide on how to better re-build, re-route & re-use the user-core.

___

___
### Outboard & input utilities

> Coherent audio platforms greatly benefit from filtering, mixing, multi-track recording, stereo & mono output Etc. these are regarded as neccessery convenience functions to the user. The idea is to make this system as modular & extensible as possible so that the partially reconfigurable part of the design is a purely intermediate step:

![FPGA IO overview diagram]()

> * FIR taps
> * Filters of arbitrary poles
> * Buck-boost converters / power switching
> * Translation into USB (or other) format
> * Signal MUXING
___

## Software / Allocator based system architecture overview

The ZYNQ-Z2 platform includes ```Dual arm A9 cores @ 650MHz``` which allow for possibilites that would either require for the FPGA to implement an expensive (& frankly unaffordable) soft core (I.e. micro-blitz, custom core). Tasks that should be run on these cores include:

* _RTOS_ or lightweight _OS_: self-explanitory. Both cores are required to implement operations that require either an RTOS or OS. I.e. to run the Allocator, serve content through the exposed _UI_ Etc...
* _Allocator_: analysis of the fabric is constantly being performed so that resources can be intelligently allocated between & within ensemble cores; a low-latency overhead environment for audio can be maintained.
* _Scripts / callbacks_: Script callbacks / event hooks can occur.
> [!IMPORTANT]
> This is on the [TODO](#todos-from-research-→-production) list
> * _Dynamic re-compilation of code_: Allow for code to be dynamically optimised based on the FPGA's runtime information

___
### ECDL (Ensemble Core Description Language)

> ECDL is a high-level common language that the end-user deploys to control the audio ensemble cores

> * Create a common descriptor and/or template level description of the desired proccessing chain
> * Hook-in callback or script functions to be executed on the arm cores on defined events
> * Translate the descriptor language into HDL (system verilog) & then a bitstream

> [!IMPORTANT]
> This is on the [TODO](#todos-from-research-→-production) list
___

## TODO'S (From research &rarr; production)

| Goal | Description | In production? (y/n) | Nature | Timeline / priority status | Complexity |
| --- | --- | --- | --- | --- | --- |
| ECDL | Translates high-level user description into fabric design, sys-calls & API calls | Y | Ongoing | Priority | High |
| Improve fabric footprint, Allocator translation | Minimise the fabric footprint & make the allocator better at optimising / translating resource division | Y | Ongoing | Priority | Very High |
| Translate Allocator to Rust | The Allocator currently runs in ```analysis``` mode which means it uses the python interpreter & Pynq bindings for debug purposes. Ideally, the Allocator should run in a more performant, but memory-safe, language like Rust. | N | Once | Medium | Medium |
| Overload / 'swap' to software based implementation if the space avaliable on the fabric is exceeded | If the FPGA doesn't have enough resources, 'intelligently' offload work from the FPGA to a software based implementation | N | Once | Low | High
| Dynamic recompilation of code | What the allocator does for the FPGA system architecture (I.e. optimising space, resource allocation, RTL design, FSM's) should be taken even further by re-compiling the code (I.e. decomposing it into less complex actions or microcode) based on FPGA runtime information | N | Once | Low | Very High