#!/usr/bin/env python3
"""
PDF-Erstellung aus Markdown-Bericht
Erstellt PDF-Version des Stakeholder-Berichts zur Fehlerfortpflanzung
"""

import os
import sys
import re
from pathlib import Path
import subprocess

def create_latex_header(project_root):
    """Erstellt LaTeX-Header für bessere Unicode-Unterstützung und Tabellen"""
    header_file = project_root / "latex_header.tex"
    header_content = r"""
\usepackage{unicode-math}
\usepackage{fontspec}
\usepackage{longtabu}
\usepackage{booktabs}
\usepackage{array}
\usepackage{pdflscape}
\usepackage{afterpage}
\usepackage{geometry}

% Unicode-Unterstützung für griechische Buchstaben
\setmainfont{DejaVu Sans}
\setmathfont{DejaVu Math TeX Gyre}

% Bessere Tabellen-Unterstützung
\usepackage{ltxtable}
\usepackage{tabularx}

% Querformat-Umgebung für große Tabellen
\newenvironment{landscapetable}{\afterpage{\clearpage\landscape\begin{table}[p]}}{\end{table}\endlandscape\clearpage}}

% Kleinere Schrift für große Tabellen
\newcommand{\tablefontsize}{\footnotesize}
"""
    
    with open(header_file, 'w', encoding='utf-8') as f:
        f.write(header_content)
    
    return header_file

def fix_markdown_issues(input_file, output_file):
    """Behebt Markdown-Formatierungsprobleme"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Sigma-Zeichen korrekt kodieren
    content = content.replace('σ', 'σ')  # Unicode Sigma
    content = content.replace('σ_', 'σ\\_')  # Escapen für LaTeX
    
    # 2. Doppelte Kapitelnummerierung entfernen - nur erste Nummerierung behalten
    # Pattern: "1.2.3 4.5 Titel" -> "4.5 Titel"
    content = re.sub(r'^(#{1,6})\s+\d+(?:\.\d+)*\s+(\d+(?:\.\d+)*\s+.*?)$', r'\1 \2', content, flags=re.MULTILINE)
    
    # 3. Große Tabelle (4.2) für Querformat markieren
    content = content.replace(
        '### 4.2 Konsolidierte Fehlerparametertabelle',
        '### 4.2 Konsolidierte Fehlerparametertabelle\n\n\\clearpage\n\\begin{landscape}\n\\tablefontsize'
    )
    
    # Ende der großen Tabelle markieren (vor nächstem Kapitel 4.3)
    content = content.replace(
        '### 4.3 Korrelationen zwischen Fehlerquellen',
        '\\end{landscape}\n\\clearpage\n\n### 4.3 Korrelationen zwischen Fehlerquellen'
    )
    
    # 4. Weitere griechische Buchstaben
    content = content.replace('ρ', 'ρ')  # Rho
    content = content.replace('α', 'α')  # Alpha
    content = content.replace('λ', 'λ')  # Lambda
    content = content.replace('μ', 'μ')  # Mu
    content = content.replace('ε', 'ε')  # Epsilon
    content = content.replace('Δ', 'Δ')  # Delta groß
    content = content.replace('τ', 'τ')  # Tau
    content = content.replace('ω', 'ω')  # Omega klein
    
    # 5. Mathematische Formeln besser formatieren
    content = re.sub(r'([σρατλμεΔτω])_(\w+)', r'\1\_\2', content)
    
    # 6. Tabellen-Formatierung für bessere PDF-Darstellung
    content = re.sub(r'\| (.+?) \|', lambda m: '| ' + m.group(1).replace('|', '\\|') + ' |', content)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

def create_pdf_from_markdown():
    """
    Konvertiert den Stakeholder-Bericht von Markdown zu PDF
    """
    # Pfade definieren
    project_root = Path(__file__).parent
    input_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.md"
    output_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.pdf"
    
    print(f"Eingabedatei: {input_file}")
    print(f"Ausgabedatei: {output_file}")
    
    # Prüfen ob Eingabedatei existiert
    if not input_file.exists():
        print(f"FEHLER: Eingabedatei nicht gefunden: {input_file}")
        return False
    
    # Versuche verschiedene PDF-Konvertierungsoptionen
    success = False
    
    # Option 1: pandoc (bevorzugt)
    try:
        print("Versuche PDF-Erstellung mit pandoc...")
        
        # Erstelle temporäre bearbeitete Markdown-Datei
        temp_md = project_root / "report" / "temp_fixed.md"
        fix_markdown_issues(input_file, temp_md)
        
        cmd = [
            "pandoc",
            str(temp_md),
            "-o", str(output_file),
            "--pdf-engine=xelatex",
            "--variable", "geometry:margin=1.5cm",
            "--variable", "fontsize=10pt",
            "--variable", "documentclass=article",
            "--variable", "mainfont=DejaVu Sans",
            "--variable", "mathfont=DejaVu Math TeX Gyre",
            "--table-of-contents",
            "--toc-depth=3",
            "--highlight-style=tango",
            "--include-in-header=" + str(create_latex_header(project_root))
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Cleanup
        if temp_md.exists():
            temp_md.unlink()
        header_file = project_root / "latex_header.tex"
        if header_file.exists():
            header_file.unlink()
            
        print("PDF erfolgreich mit pandoc erstellt!")
        success = True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"pandoc fehlgeschlagen: {e}")
        # Cleanup auch bei Fehler
        temp_md = project_root / "report" / "temp_fixed.md"
        if temp_md.exists():
            temp_md.unlink()
    
    # Option 2: weasyprint (Fallback)
    if not success:
        try:
            print("Versuche PDF-Erstellung mit weasyprint...")
            import markdown
            import weasyprint
            
            # Markdown zu HTML konvertieren
            with open(input_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Markdown-Extensions für bessere Tabellen und Formatierung
            html = markdown.markdown(
                md_content, 
                extensions=['tables', 'fenced_code', 'toc']
            )
            
            # HTML-Template mit CSS
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Fehlerfortpflanzung in Lokalisierungssystemen</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        font-size: 11pt;
                        line-height: 1.4;
                        margin: 2cm;
                        color: #333;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #2c3e50;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                    }}
                    h1 {{ font-size: 20pt; border-bottom: 2px solid #2c3e50; }}
                    h2 {{ font-size: 16pt; border-bottom: 1px solid #bdc3c7; }}
                    h3 {{ font-size: 14pt; }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1em 0;
                    }}
                    table, th, td {{
                        border: 1px solid #bdc3c7;
                    }}
                    th, td {{
                        padding: 8px;
                        text-align: left;
                        font-size: 9pt;
                    }}
                    th {{
                        background-color: #ecf0f1;
                        font-weight: bold;
                    }}
                    code {{
                        background-color: #f8f9fa;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-family: "Courier New", monospace;
                        font-size: 9pt;
                    }}
                    pre {{
                        background-color: #f8f9fa;
                        padding: 10px;
                        border-radius: 5px;
                        border-left: 4px solid #3498db;
                        overflow-x: auto;
                        font-size: 9pt;
                    }}
                    .page-break {{
                        page-break-before: always;
                    }}
                    @page {{
                        margin: 2cm;
                        @bottom-right {{
                            content: "Seite " counter(page);
                        }}
                    }}
                </style>
            </head>
            <body>
                {html}
            </body>
            </html>
            """
            
            # PDF erstellen
            weasyprint.HTML(string=html_template).write_pdf(str(output_file))
            print("PDF erfolgreich mit weasyprint erstellt!")
            success = True
            
        except ImportError:
            print("weasyprint nicht verfügbar. Installation mit: pip install weasyprint markdown")
        except Exception as e:
            print(f"weasyprint fehlgeschlagen: {e}")
    
    # Option 3: markdown-pdf (weitere Alternative)
    if not success:
        try:
            print("Versuche PDF-Erstellung mit markdown-pdf...")
            cmd = ["markdown-pdf", str(input_file), "-o", str(output_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("PDF erfolgreich with markdown-pdf erstellt!")
            success = True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"markdown-pdf fehlgeschlagen: {e}")
    
    if success:
        print(f"\n✓ PDF erfolgreich erstellt: {output_file}")
        print(f"  Dateigröße: {output_file.stat().st_size / 1024:.1f} KB")
        return True
    else:
        print("\n✗ PDF-Erstellung fehlgeschlagen!")
        print("\nMögliche Lösungen:")
        print("1. pandoc installieren: https://pandoc.org/installing.html")
        print("2. Python-Pakete installieren: pip install weasyprint markdown")
        print("3. Markdown-pdf installieren: npm install -g markdown-pdf")
        return False

if __name__ == "__main__":
    print("=== PDF-Erstellung Stakeholder-Bericht ===")
    success = create_pdf_from_markdown()
    sys.exit(0 if success else 1)