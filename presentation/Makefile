TECTONIC := $(HOME)/.local/bin/tectonic

slides.pdf: slides.tex theme.tex $(wildcard secciones/*.tex) $(wildcard figuras/*.pdf)
	$(TECTONIC) slides.tex

clean:
	rm -f slides.pdf
