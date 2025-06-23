# Project structure

Everything under ```Src``` is designed to be structured in a way that is as modular (in terms of documentation, at-least) as possible. Every folder under ```Src/RTL``` should have a ```README.md``` describing what each component does and how it is a part of the overall system architecture. Diagrams are great too!

> [!TIP]
> Imagine you've no idea what this project does. You should be able to naively navigate to any of the folders describing the system architecture \& say "**oh** so *that's* what this does." That's the principle at least.

# Syntax

## Python

### Be careful about introducing core dependencies into Allocator/Interpreter

Modules outside of the Allocator can depend upon the allocator but **NOT** vice versa. I.e. allocator must be completely seperate from ```Scripts``` other python modules Etc.
Additionally, all dependencies / libraries introduced into Allocator have to be reviewed while this is not necessarily the case for elsewhere. All dependencies will have to
play well with cpython, in addition to being performant & secure.

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
