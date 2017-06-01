all: report.pdf
	open report.pdf

report.pdf: report.tex report.bib
	pdflatex report
	bibtex report
	pdflatex report
	pdflatex report
