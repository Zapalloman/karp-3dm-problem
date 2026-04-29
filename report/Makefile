# Makefile for 3DM report
# Primary engine: tectonic (auto-downloads packages, no biber required)
# Fallback: latexmk -pdf or pdflatex+bibtex+pdflatex+pdflatex

SRCS = informe.tex preamble.tex refs.bib \
       $(wildcard secciones/*.tex) \
       $(wildcard tablas/*.tex) \
       $(wildcard figuras/*.pdf)

.PHONY: all clean

all: informe.pdf

informe.pdf: $(SRCS)
	@if command -v tectonic >/dev/null 2>&1; then \
		echo "Using tectonic..."; \
		tectonic -X compile --reruns 2 informe.tex; \
	elif command -v latexmk >/dev/null 2>&1; then \
		echo "Using latexmk..."; \
		latexmk -pdf -interaction=nonstopmode -halt-on-error informe.tex; \
	else \
		echo "Using pdflatex+bibtex..."; \
		pdflatex -interaction=nonstopmode informe.tex; \
		bibtex informe; \
		pdflatex -interaction=nonstopmode informe.tex; \
		pdflatex -interaction=nonstopmode informe.tex; \
	fi

clean:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -C; \
	else \
		rm -f informe.aux informe.bbl informe.bcf informe.blg \
		      informe.log informe.out informe.toc informe.run.xml; \
	fi
