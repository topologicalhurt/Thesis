#!/bin/bash

cd "$(dirname "$0")"

echo "Compiling presentation..."
pdflatex presentation.tex
pdflatex presentation.tex  # Run twice for proper references

echo ""
echo "Presentation compiled successfully!"
echo "Output: presentation.pdf"
echo ""
echo "To view: open presentation.pdf"
