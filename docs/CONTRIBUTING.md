## .ipynb files

If you didn't manually clear the cache for a .ipynb file one of the pre-commit hooks will do that automatically. However, the changes can't be included as part of that commit and have to be manually re-staged. A file with a name like ```fn_fixes.ipynb``` if the original notebook was ```fn.ipynb``` should appear in the same directory. Replace ```fn.ipynb``` with the fixes I.e.

```
mv docs/Notebook/filter_design_fixes.ipynb docs/Notebook/filter_design.ipynb
```
