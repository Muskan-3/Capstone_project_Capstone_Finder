# Data notes — source workbook vs. the build brief

Source file: `backend/data/source.xlsx`
(`Final-Capstone-project - Problem statement (1).xlsx`), sheet
`QUANTUM PROBLEM TITLS & STATMNT`, header on row 8, 200 data rows (rows 9–208).

The brief's Section 3 predicted **1 duplicate ID, 2 missing titles, 4 missing
statements**. Ingestion actually flags **13 rows** now, because the workbook has
been edited since the brief was written (e.g. `ASAC-CAP-PROJ-700` "FACET" was
added, beyond the faculty verification range) and because the rules catch a few
genuinely-dirty rows the brief's quick count missed. The rule is *flag, never
crash, never drop* — every flagged row below is genuinely not usable for
matching as-is, and every one stays in the DB and shows up in the admin
**Needs Review** queue.

| Source row | Project ID | Flag | Why |
|---:|---|---|---|
| 9   | `ASAC-CAP-PROJ-562`   | `duplicate_project_id` | same ID as row 70, different title — **matches brief** |
| 70  | `ASAC-CAP-PROJ-562-B` | `duplicate_project_id` | second occurrence, internal ID suffixed `-B`, `original_project_id` kept — **matches brief** |
| 23  | `ASAC-CAP-PROJ-515`   | `missing_title` | Title cell is empty — **matches brief** |
| 56  | `ASAC-CAP-PROJ-548`   | `missing_title` | Title cell is empty — **matches brief** |
| 145 | `ASAC-CAP-PROJ-637`   | `missing_title` | Title is the single character `v` — extra vs. brief |
| 167 | `ASAC-CAP-PROJ-659`   | `missing_title` | Title is `uu` — extra vs. brief |
| 15  | `ASAC-CAP-PROJ-507`   | `missing_statement` | Statement cell is the literal number `0` — **matches brief** ("literal numbers like 0") |
| 178 | `ASAC-CAP-PROJ-670`   | `missing_statement` | Statement cell is the literal number `2` — **matches brief** |
| 108 | `ASAC-CAP-PROJ-600`   | `missing_statement` | Statement cell is empty |
| 196 | `ASAC-CAP-PROJ-688`   | `missing_statement` | Statement cell is empty |
| 208 | `ASAC-CAP-PROJ-700`   | `missing_statement` | Statement cell is empty (row added after the brief) |
| 24  | `ASAC-CAP-PROJ-516`   | `missing_statement` | Statement only repeats the title verbatim — no problem description |
| 68  | `ASAC-CAP-PROJ-560`   | `missing_statement` | Statement only repeats the title verbatim |

## Other real-world messiness left intentionally untouched

Several rows (e.g. 177, 195–197, 203–208) have a **title and statement that are
about different topics** — a data-entry row shift in the source. These are *not*
flagged: both fields contain real text, so the statement is still matchable, and
"repair the shift" is not something a rule can do safely without a human. They
surface naturally in the admin corpus browser for manual fixing. This is the same
kind of issue the FACULTY DETAILS sheet already tracks by hand
(`"84 and 85 are identical"`, `"177 - No Problem Statement is available"`).

## FACULTY DETAILS sheet

Not used as a scoring signal. It is a review-assignment tracker
(`Sno`, `Faculty Name`, `Problem Statements Verified` as ranges like `1-20`,
free-text notes). The `faculty_preferences` table + admin form exist and are
ready; `weight_faculty` stays `0.0` until real preference data is entered.

## Domain balance

Of the 200 rows, only **3** have no quantum vocabulary at all (rows 23, 204,
208), and 23 + 208 are flagged — so the active pool is ~185 quantum + a handful
of quantum-titled-but-ecology-bodied statements. This is why clustering + a
routing confidence gate matter: a non-quantum student profile falls below the
gate and gets the honest low-confidence response instead of 185 quantum matches.
