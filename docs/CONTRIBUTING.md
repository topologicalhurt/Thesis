## Project structure

Everything under SRC is designed to be structured in a way that is as modular (in terms of documentation, at-least) as possible. Every folder under ```Src/RTL``` should have a README.md describing what each component does and how it is a part of the overall system architecture. Diagrams are great too!

Imagine you've no idea what this project does. You should be able to naively navigate to any of the folders and see "oh so that's what this does." That's the idea at least.

## Syntax

### Python

https://peps.python.org/pep-0008/

### System Verilog / Verilog

*A word on SV vs Verilog*: System verilog is preferred. If you see some verilog it was more than likely externally introduced.

https://github.com/lowRISC/style-guides/blob/master/VerilogCodingStyle.md

## Scripts

### Wrappers:

Any scripts introduced under ```Src``` must be written in python. Specifically, please write all scripts in **python 3.11+** for cross-platform compatability & consistency reasons. The ```Src/RTL/Scripts``` directory is where you should put them. Please strive to make these as portable and cross-platform friendly as possible - the versioning and system maintenance of verilog wrappers shouldn't be anyone's business.

### Developer:

Scripts ran as part of devops should be written in shell. This includes scripts under ```.git``` ```setup.sh``` etc... If the script is doing something particularly complicated (say you made your own linter or your own pre-commit type script) python is O.K as well - just not preferred. The reason for this is **to emphasize that this project is intended to be developed on unix-like systems!**. 

## .ipynb files

If you didn't manually clear the cache for a .ipynb file one of the pre-commit hooks will do that automatically. However, the changes can't be included as part of that commit and have to be manually re-staged. If the original notebook was ```fn.ipynb``` A file with a name like ```fn_fixes.ipynb``` should appear in the same directory. Replace ```fn.ipynb``` with the fixes I.e.

```
mv docs/Notebook/filter_design_fixes.ipynb docs/Notebook/filter_design.ipynb
```

Then re-stage the modified files (it's recommended to apply the fix straight away before working):
```
git add -U
git commit
```
