# M1 starter kit

Rename the folder to `M1_G07` (your group id from the group mail; BSED: `M1_B01`),
fill it in, and zip **the contents** as `M1_G07.zip`.

```
manifest.yaml       fill in -- read by a script, keep the keys
report.tex          the required sections in order; delete the % PROMPT lines
analysis.py         Python route: loads your slice
slice_knime.md      KNIME route: the same as nodes or one SQL query
check_submission.py + slices.csv    the self-check
```

Python or KNIME: use one route, delete the other. A `.knwf` counts as code.
**`report.pdf` is what is graded** (build with `pdflatex report.tex`, twice, or any
tool). Every figure goes into report.pdf. No folders.

Before you upload: `python3 check_submission.py M1_G07.zip`. It checks names and
numbers, not the work.

The task is `M1_sheet.pdf`, how to hand in is `HANDIN.pdf`; both win over this file.
