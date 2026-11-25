# Freedom Bag Tag print files

`build_tag.py` turns `tag_text.txt` into files a printer can use:

- `freedom-bag-tag-v2.pdf`, one 4 x 2.5 inch tag per page. Page 1 is the Spanish front and
  page 2 is the English back.
- `freedom-bag-tag-v2-sheet.pdf`, eight tags on a US Letter page. Page 1 holds the fronts and
  page 2 the backs, with the columns mirrored so they line up when printed double-sided on
  the long edge.
- `freedom-bag-tag-v2-front.png` and `freedom-bag-tag-v2-back.png` at 300 dpi.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python build_tag.py          # writes to out/, which git ignores
```

The tag text must match the Spanish and English blockquotes on `preservation.qmd`. The
script checks this before it builds and stops if they differ, so change both together.

The printed web address is `WEB_ADDRESS` at the top of `build_tag.py`. It is the bare
domain because copyleftcultivars.org currently forwards every path to the home page.

`scripts/check_tag_page.py` checks the page and this text for wording we don't use.
