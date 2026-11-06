# iMouse course-project submission package

Prepared in English from the supplied iMouse archive and CVPR template.

## Deliverables

- `iMouse_Presentation.pptx`: 19 editable slides, with speaker notes, native tables/charts and an overview diagram.
- `iMouse_Report.pdf`: CVPR-style report with references and complete project-code appendix.
- `latex/main.tex`: editable LaTeX source. Upload the contents of `latex/` to an Overleaf project and select `main.tex` as the main document.
- `DEMO_AND_VIVA_GUIDE.md`: setup, demonstration, likely questions and experiment protocol.
- `SOURCES.md`: research links, repository links, data provenance and source roles.
- `PRESENTATION_SPEAKER_NOTES.md`: standalone slide-by-slide speaking guide.
- `code/`: the original supplied project, including its existing comments, tests, demo, baseline and result logs. Application source has not been modified by this documentation task.

## Before submission

1. Edit `latex/metadata.tex` with every group member's name, roll number and actual contribution. Add/remove member fields and author lines as needed.
2. Set the submitting member and their specific contribution separately for each submitted copy. Compile again after each change.
3. Replace the final revised GitHub repository placeholder with a real URL and submitted commit. The baseline URL does not establish that the improved revision has been published. No repository was created or published during this task.
4. Update the matching fields on presentation slides 1 and 19.
5. Run the webcam and desktop demo locally. The evidence currently supports offline/synthetic behavior; do not relabel it as live-user accuracy.
6. If you complete live trials, replace the planned-experiment discussion with actual methods, counts, measurements and limitations. Preserve the scope labels on existing results.
7. Submit the report yourself through HelloIITK by **6 November 2026**. Each member must submit a copy with their own contribution. Presentation/code examination is **7–8 November 2026**, with schedule and venue to come from the instructor.

## Compile locally

From `latex/`:

```bash
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The report uses the supplied CVPR 2026 style in a named-author, page-numbered mode. The instructor's Overleaf URL currently resolves to the CVPR 2026 template despite containing `cvpr-2022` in its path. This is a course report, not an assertion of CVPR submission. No page limit was provided; the full code appendix is intentionally included.

## Evidence status

- Fresh check: 33/33 regression tests passed.
- Fresh check: deterministic synthetic gesture and jitter results reproduced exactly.
- Existing archive evidence: offline Face Mesh pipeline timings and isolated PyAutoGUI pause benchmark.
- Not measured here: webcam/desktop interaction, human accuracy, target acquisition, user fatigue and complete physical-action-to-screen latency.

The old PDF inside `code/` is a historical artifact with outdated behavior/results. Use the newly prepared report for this revised implementation. Its raw project source is preserved for provenance.
