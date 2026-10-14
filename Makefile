# ECESRIP — one entrypoint for everything in the project.
#
#   make setup    install the toolchain (iverilog, yosys, espresso, python deps)
#   make check    verify the toolchain works end to end  (~1 min)
#   make audit    regenerate every headline number from source
#   make n256     the full N=256 run: care sets -> espresso -> RTL -> iverilog
#   make schedule the colouring result: colouring vs parity, values vs labels
#   make inertial inertial vs transport delay semantics
#   make figures  redraw the patent figure set
#   make report   rebuild REPORT.pdf from REPORT.md
#   make clean    remove generated artifacts (keeps committed results)

PY := python3
CLK := phase2/clockless
PAPER := phase2/paper

.PHONY: all setup check audit n256 schedule inertial figures report clean help

help:
	@sed -n 's/^#   //p' Makefile

setup:
	@./setup.sh

check:
	@$(PY) tools/check_toolchain.py

audit:
	@$(PY) $(PAPER)/audit_claims.py

n256:
	@$(PY) $(CLK)/rtl_n256.py --N 256 --M 4 --degree 16 --radius 3

schedule:
	@$(PY) $(CLK)/analyze_coupling.py

inertial:
	@$(PY) phase2/phase10_glitch/inertial_required.py

figures:
	@cd phase2/patent_figures && $(PY) figs_1_5.py && $(PY) figs_6_11.py && $(PY) figs_12.py
	@cd phase2/patent_figures && $(PY) -c "import pymupdf,glob; \
o=pymupdf.open(); [o.insert_pdf(pymupdf.open(f)) for f in sorted(glob.glob('out/fig*.pdf'))]; \
o.save('out/patent_figures.pdf'); print('wrote out/patent_figures.pdf', o.page_count, 'pages')"

report:
	@$(PY) $(PAPER)/make_report_pdf.py

clean:
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -name '*.vvp' -delete 2>/dev/null || true
	@echo "cleaned"
