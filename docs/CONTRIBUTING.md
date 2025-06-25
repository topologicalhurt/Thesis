# Project structure

Everything under ```Src``` is designed to be structured in a way that is as modular (_in terms of documentation, at-least_) as possible. Every folder under ```Src/RTL``` should have a ```README.md``` describing what each component does and how it is a part of the overall system architecture. Diagrams are great too!

> [!TIP]
> Imagine you've no idea what this project does. It's your first time reading through all the documentation and you're overwhelmed with no idea of where to start. This is one of the central dilemnas facing open source or monolithic projects. The philosophy of this project is that any potential developer should be able to naively navigate to any one of the folders describing the system architecture, look at the README.md contained in that subdirectory (_Note: as mentioned above, it is a requirement that every system component in the RTL is described in a README.md with a link to the wiki_) and have an idea of where to start afterwards.

Every one of these README.md's should have:

- [x] A link to the wiki

- [x] A link to the corresponding testbench README.md section for the component (_Note: this is also a strong requirement_)

- [x] A link to the corresponding research documentation under ```Docs``` (if applicable)

- [x] A table with the TODO's, in the following format:

| TODO item | TODO description | Requires knowledge of (co-requisite with) | File name | Entry modules |
|-----------|------------------|-------------------------------------------|-----------|---------------|
|           |                  |                                           |           |               |
|           |                  |                                           |           |               |

- [x] A description of what each 'hardware' component is supposed to achieve in the overarching (overall) system design. Should be a paragraph at the top of the file.

- [x] A list of potential bugs & unintended behaviour.

- [x] A paragraph at the bottom with anything noteworthy.

- [ ] _Optional, but recommended_: A conclusion & abstract

# Must-do's

> [!WARNING]
> These are non-negotiables that will result in your pull request being rejected if they are not followed

## Python

### Be careful about introducing core dependencies into Allocator/Interpreter

Modules outside of the Allocator can depend upon the allocator but **NOT** vice versa. I.e. allocator must comply with:
A. Being completely abstracted away from (_that is, not reliant upon whatsoever_)```Scripts```, ```Docs``` or any other local python modules in this project.
B. All dependencies / libraries introduced into Allocator have to be reviewed. This is not necessarily the case for elsewhere.
C. All dependencies must 'play well' with cpython, in addition to being performant & secure.

# Syntax & tips

> [!TIP]
> These are **strongly held** but not strictly necessary syntax requirements. 99+% of the time they should be followed, but it is feasible that breaking one might be required. These will be reviewed on a case by case basis. Not following them will almost always result in a pull request being rejected.

## Python

### Style guideline

https://peps.python.org/pep-0008/

### Todo's

Put todo lists underneath the document docstring in order of priority E.G.

```python3
#TODO:
# 1. Most important
# 2. Second most important
...
```

### Dealing with circular imports

In general circular imports *should be avoided* but, rarely, it might make sense to not refactor definitions into another file. E.G. the misc. utility file ```helpers``` might need to call upon a common type definitions file E.G. ```dataclasses``` which itself depends upon helpers.

Let's say ```module a``` needs $x$ from ```module b``` which needs $y$ from ```module a```. The standard / preferred way to deal with this is:

#### *In module a:*
```python3
# Declare this ~BEFORE~ calling the import so it can be dynamically resolved
y = 'foo a'

b = importlib.import_module('.b', package='package_name')
x = b.x

```

#### *In module b:*
```python3
# Same as before
x = 'bar b'

a = importlib.import_module('.a', package='package_name')
y = a.y
```

Now module a will dynamically retrieve what it needs from module b without getting anything more \& vice versa!

### Dataclasses

Don't use tuples or dictionaries to pass or return complex data types. Encapsulate the data in a dataclass
(*see: https://docs.python.org/3/library/dataclasses.html*) and place it under the respective ```dataclasses.py```.

### Enums

Enums, like Dataclasses, should be stored underneath ```dataclasses.py```. Any time you would use a simple state or a tuple (implement via. the ```ExtendedTuple``` class) use an Enum instead.

___
## System Verilog / Verilog

### Style guideline

https://github.com/lowRISC/style-guides/blob/master/VerilogCodingStyle.md

**A word on SV vs Verilog**: System verilog is preferred. If you see some verilog it was more than likely externally introduced.

___
# Scripts / Misc.

## Wrappers:

Any scripts introduced under ```Src``` must be written in python. Specifically, please target **python 3.11+** (although **python3.9** is the minimum spec) for cross-platform compatability & consistency reasons. The ```Src/RTL/Scripts``` directory is where you should put them. Please strive to make these as portable \& cross-platform friendly as possible. This project strives to catalogue \& maintain verilog wrapper and/or system scripts in a manner where they are as robust \& reflective of the current RTL design as possible.

## Developer:

Scripts ran as part of devops should be written in shell. This includes scripts under ```.git``` ```setup.sh``` etc... A caveat to this is if the script is doing something particularly complicated (say you made your own linter or your own pre-commit type script) python is preferred. The reason for this is **to emphasize that this project is intended to be developed on unix-like systems!**.

## .ipynb files

### Purpose

.ipynb files should be introduced only under docs. They are designed to reflect the more technical or complicated research components of the project which is always ongoing.

### Cache clearing

If you didn't manually clear the cache for a .ipynb file one of the pre-commit hooks will do that automatically for you. However, the changes can't be included as part of that commit and have to be manually re-staged. If the original notebook was ```fn.ipynb``` A file with a name like ```fn_fixes.ipynb``` should appear in the same directory. Replace ```fn.ipynb``` with the fixes I.e.

```
mv docs/Notebook/filter_design_fixes.ipynb docs/Notebook/filter_design.ipynb
```

Then re-stage the modified files (it's recommended to apply the fix straight away before working):
```
git add -U
git commit
```
