[![Follow](https://img.shields.io/github/followers/topologicalhurt?label=Follow&style=social)](https://github.com/topologicalhurt)
[![Sponsor](https://img.shields.io/badge/Sponsor-❤️-pink?style=social)](https://github.com/sponsors/topologicalhurt)
[![Stars](https://img.shields.io/github/stars/topologicalhurt/Thesis?style=social)](https://github.com/topologicalhurt/Thesis)
[![Build Status](https://img.shields.io/github/actions/workflow/status/topologicalhurt/Thesis/ruff.yml?branch=main)](https://github.com/topologicalhurt/Thesis/actions)

# LLAC (Low Latency Audio Core dynamic allocator, platform & architecture for FPGA's)

<img width="738" alt="image" src="https://github.com/user-attachments/assets/5120e3a0-d098-4a57-b702-7936305145d4"/>

LLAC started as a research project for low-latency user defined audio cores. It targets the AMD [Xilinx](https://github.com/xilinx) platform, specifically the [PYNQ](https://github.com/Xilinx/PYNQ) platform. The project has the following goals:

1. **Allow for highly parallel FX, synthesis, mixing, filtering possibilities etc...** should exploit superior multi-channel processing capabilities offered by FPGA's
2. **Minimise the resource & time intensiveness of [kernels](#Kernels) as much as possible** (but not to the detriment of fidelity unless otherwise specified)
3. **Minimise latency, maximise throughput of kernels as much as possible**
4. **Emulate modern audio synthesis hardware as much as possible** (specifically, in regard to the fact that the analogue characteristics of kernel's should be as close to their hardware siblings as possible - just in the form of a low-level RTL system rather than an ASIC or Soft Core.)
5. **Allow for extensible IO options**
6. **Allow for the platform to be user-configurable, with low-barrier to entry** in a way not offered by un-extensible, non-reusable & non-configurable platforms.
7. **Allow for the design to be as predictive as possible, and as un-reactive as possible**

> [!INFO]
> This README is not a substitute for the whitepaper / thesis included under ```docs```. That is the real 'jumping off' point for the project: it's motivations, it's context, it's design & it's theoretical underpinnings. This is more of a 'lax' / casual description of how the project is structured and what someone can expect from it.

## Requirements

- python3.10+
- docker
- verilator
- appropriate Xilinx FPGA vendor software (E.g. Vivado)

The ```setup.sh``` script is designed as a 'one-shot' method to install all needed dependencies, with full-support for the docker.

## FPGA based system architecture overview

Because the aforementioned goals have such good synergy & parity with an FPGA based design, it follows that an implementation of a DSP environment on an FPGA might be a good idea - might just be able to be taken into the realm of configurability. The following section provides a broad-level overview of the hardware architecture involved in the project.

___
### _Static_ hardware elements

The focus of the initial research was to allow for user-configurable 'modules' called *kernels* to be dynamically configured on the fabric using a common description language. These kernels depend upon other conventional, in-built DSP modules or operations in order to function. In other words, anytime something is referred to as 'static' it is a direct shorthand for: *"exists on the fabric at all times; a direct part of the system architecture."* These parts can be categorised as falling under any combination of the following:

> * Necessary / expected elements: the configurable kernels depend upon certain axiomatic operations like trig functions, IP cores Etc.
> * Elements that are critical to the processing chain, but might not cause it to directly fail: cause artefacts, errors or incorrectness when removed.
> * Frequently called elements (I.e. in much the same way that a hot-path might have hand-rolled assembly, these elements are often frequently called & already optimised. They're expected to be used so often in almost any configurable kernel that they may as well just be outright included and re-referenced.)
> * Elements that significantly interleave with communication: this could be AXI, communication protocols, IO or otherwise needed to interlink modules, report metadata Etc.
> * Expensive, or otherwise makes little to no sense for the component to be completely reconfigurable.

> [!NOTE]
> Examples include: two-pole / second order filters *(I.e. necessary)*, truncation or readback modules *(I.e. critical to processing chain but might not be neccessary)*, mix-down operations & certain FX like delay *(I.e. frequently called)*, most typical IP cores like cordics, LUTS etc. *(I.e. significantly interleave with communication)*, functions like FFT, LAPLACE, DCT, VOLTARRE *(I.e. a combination of highly optimised, frequently called, expected, expensive or makes little sense to reconfigure)*.

___
### _User configurable kernels_ / Audio _ensemble cores_

*User configurable kernels*, used interchangeably with *Audio ensemble cores*, are the partially reconfigurable 'crux' of the project components that are uploaded to the board as part of the toolchain. They depend upon a netlist / heirarchy of other elements which compositely change the signal. **The very big-picture of this project is that to enable as many of these cores as possible, in a way that preserves non-linearities as best as possible AND with as strict a tolerance as possible on latency, timing & throughput as possible we have to intelligently schedule hardware.** There are essentially 4 ways of doing this:

- **Predicting / anticipating the evolving demands of a signal:** By "dynamically predicting the future workload" of the signal we can more intelligently decide what type of resources it will call upon. I.e. the kernel is going to use a-lot of trig functions at a low precision but require a-lot of DSPS? Load in the LUT implementation of trig functions, rather than their polynomial DSP implementation, offseting resource usage from the DSPS and speeding up the computation.
- **Swapping kernels via DFX:** This is implicit in the idea above. Sometimes a kernel will implement a really complex functionality that can't be loaded at once E.g. an RF power amplifier, an AMP sim, a filter ladder. Sometimes it will use one module once and never again (I.e. we could observe this by it's zero-input or impulse response.) Under these circumstances, it makes sense that we would want to swap out the module itself or dependencies of the module to reserve resources.
- **Tricks that involve treating a composite chain as a much simpler single block or approximation:** If we have the entire time domain (sample) or know the signal transformation is steady-state or periodic over a reasonable interval then we might be able to roll a kernel described as a complex composite of blocks / dependencies into a single kernel. Wherever possible, we want to reduce the dimension & order of the implementation so-long as the isomorphic form is meets the tolerance requirements.
- **Negotiating between kernels:** If the optimisations above fail & the head-room is needed, then we might have to sacrifice fidelity or throughput according to preference. The implementation is intelligent enough that it can settle back into a local-minima of sorts by allowing kernels to 'talk' to each other & decide what introduced errors are acceptable, at the gain of more resources.

___
### Outboard & input utilities

Audio platforms greatly benefit from filtering, mixing, multi-track recording, stereo & mono output Etc. these are regarded as neccessery convenience functions to the user in this project. Another big idea is that the partially reconfigurable part of the design is a purely intermediate step (in the sense of sound synthesis being completely abstracted away from where it is input and output). In utilities &#8594; User kernels & supporting system kernels &#8594; Out utilities is the principle here.

![FPGA IO overview diagram](docs/imgs/IOOverview.svg)

Planned outboard utilities include:

> * Amplification (class-d)
> * Buck-boost converters / power switching
> * Translation into USB (or other) format
> * Translation into CODEC
> * Signal MUXING

___
### _Deferred analysis_ components

These are components that collect metrics or information about the system as it runs. For instance, one of the most essential metrics is how many times (how frequently) a kernel calls other kernels.

___
### _Connections_ (Buses, Pipes, AXI etc...)

> [Kernels](#Kernels) need to communicate with each other, the on-chip or on-board infrastructure (_I.e. See: [Pynq Z-2 docs](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/695/DFR0600_Web.pdf)_ & need to frequently report their status, accesses & other metadata needed for hardware scheduling.

___
## Software / Allocator based system architecture overview

The ```PYNQ-Z2``` platform includes ```Dual arm A9 cores @ 650MHz``` which allows the implementation to perform tasks better suited to soft-core tasks. These include:

* _RTOS_ or lightweight _OS_: Both cores are required to implement operations that require either an RTOS or OS. I.e. to run the Allocator, serve content through the exposed _UI_ Etc...
* _Allocator_: analysis of the fabric is constantly being performed not on the FPGA itself but on soft-cores
* _Scripts / callbacks_: Script callbacks / event hooks can occur. I.e. kernel specifies interrupt after operation x &#8594; FPGA does operation x &#8594; Soft-core takes over &#8594; Specified script is run &#8594; Control restored back to FPGA kernel

> [!IMPORTANT]
> This is on the [TODO](#todos-from-research-→-production) list:
> * _Dynamic re-compilation of code_: Allow for code to be dynamically optimised on the soft-core through use of JIT compiler

___
### ECDL (Ensemble Core Description Language)

ECDL is a high-level common language that mixes in template language descriptions. It is used to deploy & control the kernels. The proposed workflow is to:

> * Implement custom logic in a HDL (optional)
> * Include a common descriptor and/or template level description of the desired processing chain. Designed to reference pre-existing modules & custom HDL
> * Hook-in callback or script functions to be executed on the arm cores on defined events (optional)
> * Perform pre-upload analysis and integration / wrapping
> * Translate the optimised descriptor language into HDL (system verilog) & then a bitstream
> * Continually monitor & track that kernel over time, I.e. it is now deployed and continues to be optimised

> [!IMPORTANT]
> This is on the [TODO](#todos-from-research-→-production) list

___
## TODO'S (From research &rarr; production)

| Goal | Description | In production? (y/n) | Nature | Timeline / priority status | Complexity |
| --- | --- | --- | --- | --- | --- |
| ECDL | Translates high-level user description into fabric design, sys-calls & API calls | Y | Ongoing | Priority | High |
| Improve fabric footprint, Allocator translation | Minimise the fabric footprint & make the allocator better at optimising / translating resource division | Y | Ongoing | Priority | Very High |
| Translate Allocator to Rust | The Allocator currently runs in ```analysis``` mode which means it uses the python interpreter & Pynq bindings for debug purposes. Ideally, the Allocator should run in a more performant, but memory-safe, language like Rust. | N | Once | Medium | Medium |
| Overload / 'swap' to software based implementation if the space available on the fabric is exceeded | If the FPGA doesn't have enough resources, 'intelligently' offload work from the FPGA to a software based implementation | N | Once | Low | High
| Dynamic recompilation of code | What the allocator does for the FPGA system architecture (I.e. optimising space, resource allocation, RTL design, FSM's) should be taken even further by re-compiling the code (I.e. decomposing it into less complex actions or microcode) based on FPGA runtime information | N | Once | Low | Very High
