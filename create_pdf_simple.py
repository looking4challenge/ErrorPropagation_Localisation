#!/usr/bin/env python3
"""
Vereinfachte PDF-Erstellung mit korrigierten Formatierungsproblemen
"""

import os
import sys
import re
from pathlib import Path
import subprocess

def fix_markdown_for_pdf(input_file, output_file):
    """Behebt die gemeldeten Markdown-Formatierungsprobleme"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Behebe Formatierungsprobleme...")
    
    # 1. Doppelte Kapitelnummerierung entfernen
    # Muster: "### 1.2.3 4.1 Titel" -> "### 4.1 Titel"
    print("- Entferne doppelte Kapitelnummerierung...")
    content = re.sub(r'^(#{1,6})\s+\d+(?:\.\d+)*\s+(\d+(?:\.\d+)+\s+.*?)$', r'\1 \2', content, flags=re.MULTILINE)
    
    # 2. Sigma und andere griechische Zeichen explizit als HTML-Entitäten
    print("- Ersetze griechische Buchstaben...")
    replacements = {
        'σ': '&sigma;',
        'ρ': '&rho;', 
        'α': '&alpha;',
        'λ': '&lambda;',
        'μ': '&mu;',
        'ε': '&epsilon;',
        'Δ': '&Delta;',
        'τ': '&tau;',
        'ω': '&omega;'
    }
    
    for greek, html in replacements.items():
        content = content.replace(greek, html)
    
    # 3. Große Tabelle 4.2 für Querformat vorbereiten
    print("- Markiere große Tabelle für Querformat...")
    
    # Finde die große Tabelle (4.2)
    table_start = content.find('### 4.2 Konsolidierte Fehlerparametertabelle')
    if table_start != -1:
        # Finde das Ende der Tabelle (nächster ### Abschnitt)
        table_end = content.find('### 4.3', table_start)
        if table_end != -1:
            # Extrahiere die Tabelle
            before_table = content[:table_start]
            table_section = content[table_start:table_end]
            after_table = content[table_end:]
            
            # Füge Querformat-Hinweise hinzu
            table_section = table_section.replace(
                '### 4.2 Konsolidierte Fehlerparametertabelle',
                '### 4.2 Konsolidierte Fehlerparametertabelle\n\n*Diese Tabelle wird im Querformat dargestellt für bessere Lesbarkeit.*\n\n<div style="page-break-before: always; transform: rotate(90deg); transform-origin: left top; width: 100vh; height: 100vw; position: absolute;">'
            )
            
            # Schließe das Querformat vor dem nächsten Abschnitt
            table_section += '\n\n</div>\n\n<div style="page-break-before: always;"></div>\n\n'
            
            content = before_table + table_section + after_table
    
    # 4. Verbessere Code-Blöcke für bessere PDF-Darstellung
    content = re.sub(r'```text\n(.*?)\n```', r'```\n\1\n```', content, flags=re.DOTALL)
    
    # 5. Füge Seitenumbrüche vor Hauptkapiteln hinzu
    content = re.sub(r'^## (\d+\.)', r'\\pagebreak\n\n## \1', content, flags=re.MULTILINE)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Korrigierte Markdown-Datei erstellt: {output_file}")

def create_pdf_simple():
    """Erstellt PDF mit einfachem pandoc-Aufruf"""
    
    project_root = Path(__file__).parent
    input_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.md"
    fixed_file = project_root / "report" / "stakeholder_bericht_fixed.md"
    output_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.pdf"
    
    print(f"=== PDF-Erstellung Stakeholder-Bericht ===")
    print(f"Eingabe: {input_file}")
    print(f"Ausgabe: {output_file}")
    
    if not input_file.exists():
        print(f"FEHLER: Eingabedatei nicht gefunden!")
        return False
    
    try:
        # 1. Markdown korrigieren
        fix_markdown_for_pdf(input_file, fixed_file)
        
        # 2. Einfacher pandoc-Aufruf
        print("Erstelle PDF mit pandoc...")
        cmd = [
            "pandoc",
            str(fixed_file),
            "-o", str(output_file),
            "--pdf-engine=pdflatex",
            "--variable", "geometry:margin=2cm",
            "--variable", "fontsize=10pt",
            "--variable", "documentclass=article",
            "--table-of-contents",
            "--number-sections",
            "--highlight-style=tango"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ PDF erfolgreich erstellt!")
            print(f"  Dateigröße: {output_file.stat().st_size / 1024:.1f} KB")
            
            # Cleanup
            if fixed_file.exists():
                fixed_file.unlink()
            
            return True
        else:
            print("✗ pandoc-Fehler:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("✗ pandoc nicht gefunden!")
        print("Installation: https://pandoc.org/installing.html")
        return False
    except Exception as e:
        print(f"✗ Unerwarteter Fehler: {e}")
        return False

if __name__ == "__main__":
    success = create_pdf_simple()
    sys.exit(0 if success else 1)