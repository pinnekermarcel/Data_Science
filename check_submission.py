r"""Check your own archive before you upload it.

    python3 check_submission.py M1_G07.zip        # from inside the kit

Checks the name, the manifest, your counts against your slice, and that report
and code are in the archive -- so nothing fails for a clerical reason. It does
not judge the work. FIX = must change, warn = read and decide.
Exit code 0 = nothing to fix. Tasks: M?_sheet.pdf; how to hand in: HANDIN.pdf.
"""
import csv
import re
import statistics
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# slices.csv beside this script (the kit), else in Portfolio/ (the repository)
_HERE = Path(__file__).resolve().parent / "slices.csv"
SLICES = _HERE if _HERE.exists() else ROOT / "Portfolio" / "slices.csv"
NAME = re.compile(r"^M([123])_((?:G|B)\d{2})\.zip$")     # what a student should TYPE
# FIX only where marking is impossible; close names and number formats are read
# as meant and, at most, pointed out.
# A database password typed in as a literal (not read from the environment).
_PW_KEY = r"(?:pass(?:word|wd)?|pwd|mysql_pwd)"
PASSWORD_QUOTED = re.compile(_PW_KEY + r"""\s*[:=]\s*\\?["'](?![$<{])[^"'\s\\]{3,}\\?["']""", re.I)
PASSWORD_PLAIN = re.compile(r"(?m)^\s*(?:export\s+)?" + _PW_KEY
                            + r"""\s*[:=]\s*(?![$<{"'\s])[^\s"'#]{3,}""", re.I)
PASSWORD_URL = re.compile(r"mysql(?:\+\w+)?://[^:/\s]+:(?![$<{])[^@\s]{3,}@", re.I)
CONFIG_EXT = (".yaml", ".yml", ".txt", ".cfg", ".ini", ".env", ".sh", ".toml")

# A re-upload to the file drop is renamed "M1_G07 (2).zip"; that name must parse.
DUP = re.compile(r"\s*\(\d+\)\s*$")
EXTS = (".tar.gz", ".tgz", ".zip")


def parse_archive(filename):
    """(milestone, group, renamed_by_server) for an archive name, or None."""
    low = filename.lower()
    for ext in EXTS:
        if low.endswith(ext):
            stem = filename[:-len(ext)]
            break
    else:
        return None
    dup = bool(DUP.search(stem))
    m = re.match(r"^M([123])[_ -]((?:G|B)\d{2})(?:[_ -].*)?$", DUP.sub("", stem).strip(), re.I)
    if not m:
        return None
    return f"M{m.group(1)}", m.group(2).upper(), dup


def slices():
    with open(SLICES, newline="") as fh:
        return {r["slice_id"]: r for r in csv.DictReader(fh)}


def number(v):
    """A reported number as a float, or None if there is none in it.

    Reads what people actually type: 396.07, '396,07', '1.234,5',
    '396.07 USD', '171.3 %' (= 1.713). A single comma is a decimal comma here;
    count() reads '2,629' as thousands, since a count has no decimals. Shared with grade_numbers.py and
    triage.py, so the three scripts can never read the same value differently.
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    pct = s.endswith("%")
    s = re.sub(r"[^\d,.\-]", "", s)          # units, spaces, apostrophes, %
    if not re.search(r"\d", s):
        return None
    if "," in s and "." in s:                 # both: the last one is decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif s.count(",") > 1:                    # 1,234,567
        s = s.replace(",", "")
    elif "," in s:                            # 396,07 and 1,713: a decimal comma
        s = s.replace(",", ".")               # (count() reads 2,629 as thousands)
    try:
        x = float(s)
    except ValueError:
        return None
    return x / 100 if pct else x


def count(v):
    """A reported count as an int, or None: 2629, 2629.0, '2,629', '2.629', '2 629'."""
    s = str(v).strip() if v is not None else ""
    if re.fullmatch(r"-?\d{1,3}([.,]\d{3})+", s):  # 2,629 / 2.629: a count has no decimals
        v = s.replace(".", "").replace(",", "")
    x = number(v)
    if x is None or abs(x - round(x)) > 1e-9:
        return None
    return int(round(x))


def read_table(csv_text):
    """(header, data rows) of a CSV as KNIME, Excel or pandas write it: comma,
    semicolon or tab, with or without a BOM, any line ending."""
    text = csv_text.lstrip("\ufeff")
    first = text.split("\n", 1)[0]
    delim = max((",", ";", "\t"), key=first.count)
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    if not rows:
        return [], []
    return [h.strip() for h in rows[0]], [r for r in rows[1:] if any(c.strip() for c in r)]


def _int(v):
    """count(), raising like int() did, for the M2 arithmetic below."""
    c = count(v)
    if c is None:
        raise ValueError(v)
    return c


def chain_checks(csv_text, man, slice_lines):
    """M2: does your own work add up? No reference values, only your own files:
    1. rows_in - rows_removed == rows_out, rows_in = your slice's raw lines;
    2. the matrix has at most one object per customer of clean_flat.csv
       (fewer is fine with a reason in dropped_because);
    3. cluster sizes + unassigned == matrix objects.
    """
    bad, warn = [], []
    try:
        header, data = read_table(csv_text)
    except Exception as e:
        return [f"clean_flat.csv cannot be read as CSV: {e}"], warn
    if not data:
        return ["clean_flat.csv has no data rows"], warn

    # ── 1. the cleaning log closes ───────────────────────────────────────────
    cl = man.get("cleaning")
    if not isinstance(cl, dict):
        bad.append("manifest: the `cleaning:` block is missing -- M2 reports "
                   "rows_in, rows_removed and rows_out (HANDIN.md 5)")
    else:
        try:
            r_in, r_out = _int(cl.get("rows_in")), _int(cl.get("rows_out"))
            # left out when nothing was removed: then it is in minus out
            r_rm = (_int(cl["rows_removed"]) if cl.get("rows_removed") not in (None, "")
                    else r_in - r_out)
        except (TypeError, ValueError):
            bad.append("manifest: cleaning.rows_in / rows_removed / rows_out "
                       "must all be numbers")
        else:
            if slice_lines is not None and r_in != slice_lines:
                bad.append(f"manifest: cleaning.rows_in says {r_in:,}, but your "
                           f"slice has {slice_lines:,} order lines. That is the "
                           "table you started from.")
            if r_in - r_rm != r_out:
                bad.append(f"manifest: the cleaning log does not close -- "
                           f"{r_in:,} in minus {r_rm:,} removed is "
                           f"{r_in - r_rm:,}, but rows_out says {r_out:,}. The "
                           "per-decision table in your report has to sum to "
                           "rows_removed.")
            if r_out != len(data):
                bad.append(f"manifest: cleaning.rows_out says {r_out:,}, but the "
                           f"clean_flat.csv in this archive has {len(data):,} "
                           "data rows")

    # ── 2. the matrix was built on the table handed in ───────────────────────
    mx = man.get("matrix")
    if not isinstance(mx, dict):
        bad.append("manifest: the `matrix:` block is missing -- M2 reports how "
                   "many objects and features its matrix has (HANDIN.md 5)")
    else:
        try:
            objects = _int(mx.get("objects"))
        except (TypeError, ValueError):
            bad.append("manifest: matrix.objects is missing or not a number")
            objects = None
        idc = next((i for i, h in enumerate(header)
                    if h.strip().lower() in ("customerid", "customer_id")), None)
        if objects is not None and idc is not None:
            have = len({r[idc] for r in data if idc < len(r)})
            if objects > have:
                bad.append(f"manifest: matrix.objects says {objects:,}, but your "
                           f"cleaned table holds only {have:,} distinct "
                           "customers. The matrix cannot have more objects than "
                           "the table it was built from.")
            elif objects < have and not str(mx.get("dropped_because", "")).strip():
                # Dropping objects is a legitimate modelling decision -- it just
                # has to be a stated one, not a silent one.
                bad.append(f"manifest: matrix.objects is {objects:,} of {have:,} "
                           "customers in your cleaned table. That may be right, "
                           "but say why in matrix.dropped_because.")

    # ── 3. the clusters cover the matrix ─────────────────────────────────────
    cls = man.get("clusters")
    if not isinstance(cls, dict):
        bad.append("manifest: the `clusters:` block is missing -- M2 reports k "
                   "and the cluster sizes (HANDIN.md 5)")
    elif isinstance(mx, dict):
        sizes = cls.get("sizes")
        if isinstance(sizes, (str, int)):          # "1389, 62" or a single k=1 size
            sizes = [x for x in re.split(r"[;,\s]+", str(sizes).strip("[] ")) if x]
        if not isinstance(sizes, list) or not sizes:
            bad.append("manifest: clusters.sizes must be a list, one count per "
                       "cluster")
        else:
            try:
                sz = [_int(x) for x in sizes]
                una = _int(cls.get("unassigned", 0))
                k = _int(cls.get("k", len(sz)))
                objects = _int(mx.get("objects"))
            except (TypeError, ValueError):
                bad.append("manifest: clusters.k / sizes / unassigned must be "
                           "numbers")
            else:
                if k != len(sz):
                    bad.append(f"manifest: clusters.k says {k} but "
                               f"{len(sz)} sizes are listed")
                if sum(sz) + una != objects:
                    bad.append(f"manifest: the clusters do not cover the matrix "
                               f"-- {sum(sz):,} in clusters plus {una:,} "
                               f"unassigned is {sum(sz) + una:,}, but "
                               f"matrix.objects says {objects:,}")
    return bad, warn


def cleaned_table_check(csv_text, man):
    """M2: rows, columns and the named median, recomputed from your clean_flat.csv."""
    bad = []
    dec = man.get("cleaned")
    if not isinstance(dec, dict):
        return ["manifest: the `cleaned:` block is missing -- M2 reports rows, "
                "columns and one median of the cleaned table it hands in "
                "(HANDIN.md 5)"]
    try:
        header, data = read_table(csv_text)
    except Exception as e:
        return [f"clean_flat.csv cannot be read as CSV: {e}"]
    if not data:
        return ["clean_flat.csv has no data rows"]

    # pandas writes its index as a nameless first column unless index=False
    ncols = len(header) - (1 if header and header[0] in ("", "Unnamed: 0") else 0)
    for key, actual, what in (("rows", len(data), "data rows"),
                              ("columns", ncols, "columns")):
        if key not in dec:
            bad.append(f"manifest: cleaned.{key} is missing")
            continue
        try:
            claimed = _int(dec[key])
        except (TypeError, ValueError):
            bad.append(f"manifest: cleaned.{key} is not a number")
            continue
        if claimed != actual and not (key == "columns" and claimed == len(header)):
            bad.append(f"manifest: cleaned.{key} says {claimed:,}, but the "
                       f"clean_flat.csv in this archive has {actual:,} {what}")

    col = str(dec.get("median_of", "")).strip()
    if not col:
        bad.append("manifest: cleaned.median_of is missing -- name the column "
                   "your median is over")
        return bad
    low = [h.lower() for h in header]
    if col.lower() not in low:
        bad.append(f"manifest: cleaned.median_of is {col!r}, which is not a "
                   f"column of your cleaned table ({', '.join(header[:8])}...)")
        return bad
    i = low.index(col.lower())
    vals = []
    for r in data:
        if i < len(r):
            x = number(r[i]) if r[i].strip() else None
            if x is not None:
                vals.append(x)
    if not vals:
        bad.append(f"manifest: cleaned.median_of names {col!r}, which holds no "
                   "numbers -- pick a numeric column")
        return bad
    actual = statistics.median(vals)
    claimed = number(dec.get("median"))
    if claimed is None:
        bad.append("manifest: cleaned.median is missing or not a number")
        return bad
    scale = max(abs(actual), 1e-9)
    if abs(claimed - actual) / scale > 0.005:
        bad.append(f"manifest: cleaned.median says {claimed:,.2f} for {col!r}, "
                   f"but that column's median in your own file is "
                   f"{actual:,.2f}")
    return bad


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 1
    p = Path(argv[0])
    bad, warn = [], []

    pa = parse_archive(p.name)
    if not pa:
        bad.append(f"the file must be named M<1|2|3>_<group>.zip -- e.g. M1_G07.zip, "
                   f"or M1_B01.zip for a BSED group -- not {p.name!r}")
    elif not NAME.match(p.name):
        warn.append(f"read {p.name!r} as {pa[0]}_{pa[1]}.zip -- fine; "
                    f"{pa[0]}_{pa[1]}.zip is the cleaner name")
    if not p.exists():
        print(f"no such file: {p}")
        return 1
    milestone = pa[0] if pa else None
    group = pa[1] if pa else None

    try:
        z = zipfile.ZipFile(p)
    except zipfile.BadZipFile:
        print("that is not a readable zip archive -- re-create it")
        return 1
    names = z.namelist()

    def find(pred):
        return [n for n in names if pred(n.lower())]

    d = None                      # bound even when there is no manifest to parse
    man = find(lambda n: n.endswith(("manifest.yaml", "manifest.yml")))
    if not man:
        bad.append("manifest.yaml is missing")
    else:
        try:
            import yaml
        except ImportError:
            warn.append("pyyaml not installed here, manifest not parsed "
                        "(pip install pyyaml)")
            yaml = None
        if yaml:
            try:
                d = yaml.safe_load(z.read(man[0]).decode("utf-8", "replace")) or {}
            except Exception as e:
                d = None
                raw = z.read(man[0]).decode("utf-8", "replace")
                hint = (" -- it contains a TAB; YAML indents with spaces only"
                        if "\t" in raw else "")
                bad.append(f"manifest.yaml is not valid YAML{hint}: "
                           + str(e).splitlines()[0])
            if d is not None and not isinstance(d, dict):
                # valid YAML, but not key: value lines
                bad.append(f"manifest.yaml is {type(d).__name__}, not a set of "
                           "key: value lines -- start from the template's copy")
                d = None
            if d is not None:
                for k in ("group", "slice_id", "milestone", "submitted_by",
                          "members", "findings"):
                    if not d.get(k):
                        bad.append(f"manifest: {k} is missing or empty")
                if group and str(d.get("group", "")).strip().upper() != group:
                    bad.append(f"manifest: group is {d.get('group')!r} but the "
                               f"filename says {group!r}")
                if milestone and str(d.get("milestone", "")).strip().upper() != milestone:
                    bad.append(f"manifest: milestone is {d.get('milestone')!r} "
                               f"but the filename says {milestone!r}")
                mem = d.get("members") or []
                if not isinstance(mem, list):
                    bad.append("manifest: members must be a list of entries, "
                               f"not a {type(mem).__name__} -- see the template")
                    mem = []
                if len(mem) < 2:
                    warn.append(f"manifest: only {len(mem)} member(s) listed")
                for i, x in enumerate(mem, 1):
                    # "- name: ... / responsible_for: ..." as in the template, or
                    # the shorter "- Anna Beispiel: profiling" -- both say it.
                    if isinstance(x, dict) and "name" not in x and len(x) == 1:
                        (k, v), = x.items()
                        x = {"name": k, "responsible_for": v}
                    elif isinstance(x, str):
                        x = {"name": x}
                    # an empty YAML value is None, and str(None) is "None"
                    nm = str((x.get("name") if isinstance(x, dict) else "") or "").strip()
                    rf = str((x.get("responsible_for") if isinstance(x, dict) else "") or "").strip()
                    if not nm or nm.startswith("<"):
                        bad.append(f"manifest: member {i} has no name"
                                   + (" (still the template's placeholder)" if nm else ""))
                    elif not rf or rf.startswith("<"):
                        bad.append(f"manifest: {nm} has an empty "
                                   f"responsible_for -- it is mandatory")
                sid = str(d.get("slice_id", "")).strip().upper()
                tr = slices().get(sid)
                if sid and not tr:
                    bad.append(f"manifest: slice_id {sid!r} is not a real slice")
                elif tr:
                    fnd = d.get("findings") or {}
                    if not isinstance(fnd, dict):
                        bad.append("manifest: findings must be name: value lines, "
                                   f"not a {type(fnd).__name__} -- see the template")
                        fnd = {}
                    # all at 0 = untouched template; a single 0 can be true
                    left = [k for k, v in fnd.items()
                            if str(v).strip() in ("0", "0.0", "")]
                    if fnd and len(left) == len(fnd):
                        bad.append("manifest: findings are all still at 0 -- "
                                   "copy them from your own output")
                    # The identity triple lives in `findings`; older manifests
                    # carry it under `reported` as well, which is still read.
                    rep = d.get("reported") if isinstance(d.get("reported"), dict) else {}
                    for k in ("lines", "orders", "customers"):
                        src = "findings" if k in fnd else "reported"
                        val = fnd.get(k, rep.get(k))
                        if val is None:
                            bad.append(f"manifest: findings.{k} is missing")
                            continue
                        got = count(val)
                        if got is None:
                            bad.append(f"manifest: {src}.{k} is {val!r}, not a count")
                            continue
                        exp = int(float(tr[k]))
                        if got != exp:
                            bad.append(f"manifest: {src}.{k} says {got:,}, "
                                       f"but slice {sid} has {exp:,} -- is "
                                       f"slice_id right, and is the filter on "
                                       f"your territory AND your category?")

    tops = {n.split("/")[0] for n in names}
    if len(tops) == 1 and all("/" in n for n in names):
        warn.append(f"everything sits in one folder {next(iter(tops))}/ -- zip the "
                    "CONTENTS of the folder, not the folder itself")
    elif find(lambda n: n.count("/") > 1):
        warn.append("deep folders in the archive -- HANDIN.md asks for a flat "
                    "layout: report.pdf, manifest.yaml, your code")
    def is_mgmt(n):
        base = n.rsplit("/", 1)[-1]
        return "management" in base or "delivery" in base
    pdfs = [n for n in find(lambda n: n.endswith(".pdf") and not is_mgmt(n))
            if "__macosx" not in n.lower()]
    if not find(lambda n: n.endswith("report.pdf") and not is_mgmt(n)) and pdfs:
        warn.append(f"no file named report.pdf -- reading {pdfs[0]} as the report"
                    + (f" (there are {len(pdfs)} PDFs: name the report report.pdf)"
                       if len(pdfs) > 1 else ""))
    elif not pdfs:
        if find(lambda n: n.endswith((".md", ".tex", ".docx"))):
            bad.append("report.pdf is missing (a .md or .tex source is not the "
                       "deliverable -- export the PDF)")
        else:
            bad.append("report.pdf is missing")

    # Milestone files: a close name is read as meant (warn), a missing file is a FIX.
    def named(exact, near):
        hit = find(lambda n: n.endswith(exact))
        if hit:
            return hit
        hit = find(near)
        if hit:
            warn.append(f"reading {hit[0]} as {exact} -- fine; {exact} is the "
                        "name the sheet uses")
        return hit
    cf = (named("clean_flat.csv", lambda n: n.endswith(".csv") and "clean" in n)
          if milestone == "M2" else [])
    if milestone == "M2" and not cf:
        bad.append("clean_flat.csv is missing -- M2 hands in the cleaned table "
                   "(HANDIN.md 4), and M3 is built on it")
    if milestone == "M2" and cf and isinstance(d, dict):
        text = z.read(cf[0]).decode("utf-8-sig", "replace")
        bad += cleaned_table_check(text, d)
        sid = str(d.get("slice_id", "")).strip().upper()
        tr = slices().get(sid)
        raw = int(float(tr["lines"])) if tr else None
        cbad, cwarn = chain_checks(text, d, raw)
        bad += cbad
        warn += cwarn
    imgs_in_dir = find(lambda n: "/" in n and n.endswith(
        (".png", ".jpg", ".jpeg", ".svg", ".pdf", ".gif", ".webp")))
    if (milestone == "M2" and not find(lambda n: "plots_before/" in n)
            and imgs_in_dir):
        warn.append(f"no plots_before/ -- reading {imgs_in_dir[0].rsplit('/', 1)[0]}/ "
                    "as the plots before the peer review")
    elif milestone == "M2" and not find(lambda n: "plots_before/" in n):
        warn.append("no plots_before/ -- fine if the five plots as they were before "
                   "the peer review are in an appendix of report.pdf (M2_sheet.pdf, Task 7)")
    if milestone == "M3" and not named("management_report_delivery.pdf",
                                       lambda n: n.endswith(".pdf") and is_mgmt(n)):
        bad.append("management_report_delivery.pdf is missing -- M3 hands in the generated report "
                   "next to report.pdf (M3_sheet.pdf, Task 6)")
    if milestone == "M3" and not named("dashboard_orders.csv",
                                       lambda n: n.endswith(".csv") and "dashboard" in n):
        bad.append("dashboard_orders.csv is missing -- M3's dashboard reads one flat "
                   "order-line table with the customer attributes joined on, and that "
                   "file is what makes it reproducible (M3_sheet.pdf, Task 1)")

    code = find(lambda n: n.endswith((".py", ".sql", ".ipynb", ".knwf", ".r",
                                      ".sh")))
    if not code:
        bad.append("no code in the archive (.py/.sql/.ipynb/.knwf) -- the "
                   "numbers have to be reproducible")

    if find(lambda n: "__macosx" in n or n.endswith(".ds_store")):
        warn.append("the archive contains __MACOSX / .DS_Store clutter")
    if find(lambda n: n.startswith(("venv/", ".venv/", ".git/"))
            or any(x in n for x in ("/venv/", "/.venv/", "/.git/"))):
        bad.append("the archive contains a venv/ or .git/ folder -- leave it out")

    meta = find(lambda n: "meta" in n.rsplit("/", 1)[-1]
                and n.endswith((".yaml", ".yml", ".json")))
    if milestone == "M1" and meta and not find(lambda n: n.endswith("awc_flat.metadata.yaml")):
        warn.append(f"reading {meta[0]} as the metadata file -- fine; "
                    "awc_flat.metadata.yaml is the name the sheet uses")
    if milestone == "M1" and not meta:
        bad.append("awc_flat.metadata.yaml is missing -- M1 hands in the metadata "
                   "file for your extract (M1_sheet.pdf, Task 7)")

    # A password typed into code or config (os.environ / $AWC_DB_PW is fine).
    # This script itself is skipped.
    for n in find(lambda n: n.endswith((".py", ".sql", ".ipynb", ".yaml", ".yml",
                                        ".txt", ".cfg", ".ini", ".env", ".sh",
                                        ".json", ".toml"))
                  and n.rsplit("/", 1)[-1] != "check_submission.py"):
        text = z.read(n).decode("utf-8", "replace")
        if (PASSWORD_QUOTED.search(text) or PASSWORD_URL.search(text)
                or (n.endswith(CONFIG_EXT) and PASSWORD_PLAIN.search(text))):
            bad.append(f"{n} seems to contain a database password -- read it "
                       "from the environment instead (HANDIN.md 6)")

    print(f"{p.name}: {len(names)} entries")
    for w in warn:
        print(f"  warn  {w}")
    for b in bad:
        print(f"  FIX   {b}")
    if not bad:
        sheet = f"{milestone}_sheet.pdf" if milestone else "your task sheet"
        print(f"  ok    nothing a script can catch. Now re-read {sheet} "
              "and HANDIN.md §6: is every task answered, every decision stated "
              "with the number behind it?")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
