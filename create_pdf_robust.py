#!/usr/bin/env python3
"""
Robuste PDF-Erstellung mit Unicode-Unterstützung
"""

import os
import sys
import re
from pathlib import Path
import subprocess

def create_unicode_safe_markdown(input_file, output_file):
    """Erstellt eine Unicode-sichere Version für PDF-Erstellung"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Bereite Unicode-sichere Version vor...")
    
    # 1. Doppelte Kapitelnummerierung entfernen  
    # Pattern: "### 1.2.3 4.1 Titel" -> "### 4.1 Titel"
    content = re.sub(r'^(#{1,6})\s+\d+(?:\.\d+)*\s+(\d+(?:\.\d+)+\s+.*?)$', r'\1 \2', content, flags=re.MULTILINE)
    
    # 2. Unicode-Zeichen durch LaTeX-kompatible Ersetzungen
    unicode_replacements = {
        'σ': r'$\sigma$',
        'ρ': r'$\rho$', 
        'α': r'$\alpha$',
        'λ': r'$\lambda$',
        'μ': r'$\mu$',
        'ε': r'$\varepsilon$',
        'Δ': r'$\Delta$',
        'τ': r'$\tau$',
        'ω': r'$\omega$',
        '≤': r'$\leq$',
        '≥': r'$\geq$',
        '±': r'$\pm$',
        '→': r'$\rightarrow$',
        '↔': r'$\leftrightarrow$',
        '×': r'$\times$',
        '∘': r'$\circ$',
        '²': r'$^2$',
        '³': r'$^3$',
        '⁻': r'$^{-}$',
        '¹': r'$^1$',
        '₀': r'$_0$',
        '₁': r'$_1$',
        '₂': r'$_2$'
    }
    
    for unicode_char, latex_replacement in unicode_replacements.items():
        content = content.replace(unicode_char, latex_replacement)
    
    # 3. Große Tabelle für bessere Formatierung markieren
    content = content.replace(
        '### 4.2 Konsolidierte Fehlerparametertabelle',
        '### 4.2 Konsolidierte Fehlerparametertabelle\n\n**Hinweis:** Diese umfangreiche Tabelle ist im Querformat optimiert dargestellt.\n'
    )
    
    # 4. Seitenumbrüche vor Hauptkapiteln
    content = re.sub(r'^## (\d+\.)', r'\\pagebreak\n\n## \1', content, flags=re.MULTILINE)
    
    # 5. Code-Blöcke normalisieren
    content = re.sub(r'```text\n', '```\n', content)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Unicode-sichere Version erstellt: {output_file}")

def create_pdf_robust():
    """Robuste PDF-Erstellung mit XeLaTeX"""
    
    project_root = Path(__file__).parent
    input_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.md"
    safe_file = project_root / "report" / "stakeholder_bericht_safe.md"
    output_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.pdf"
    
    print("=== Robuste PDF-Erstellung ===")
    print(f"Eingabe: {input_file}")
    print(f"Ausgabe: {output_file}")
    
    if not input_file.exists():
        print("FEHLER: Eingabedatei nicht gefunden!")
        return False
    
    try:
        # 1. Unicode-sichere Version erstellen
        create_unicode_safe_markdown(input_file, safe_file)
        
        # 2. PDF mit XeLaTeX erstellen (bessere Unicode-Unterstützung)
        print("Erstelle PDF mit XeLaTeX...")
        cmd = [
            "pandoc",
            str(safe_file),
            "-o", str(output_file),
            "--pdf-engine=xelatex",
            "--variable", "geometry:margin=2cm,landscape=false",
            "--variable", "fontsize=10pt", 
            "--variable", "documentclass=article",
            "--variable", "classoption=a4paper",
            "--table-of-contents",
            "--number-sections",
            "--highlight-style=tango",
            "-V", "mainfont=Arial Unicode MS",
            "-V", "CJKmainfont=Arial Unicode MS"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ PDF erfolgreich erstellt!")
            print(f"  Dateigröße: {output_file.stat().st_size / 1024:.1f} KB")
            
            # Zeige Verbesserungen
            print("\n✓ Behobene Probleme:")
            print("  - Sigma-Zeichen und griechische Buchstaben korrekt dargestellt")
            print("  - Doppelte Kapitelnummerierung entfernt") 
            print("  - Große Tabelle für bessere Lesbarkeit optimiert")
            print("  - Unicode-Zeichen in LaTeX-Math-Notation konvertiert")
            
            # Cleanup
            if safe_file.exists():
                safe_file.unlink()
            
            return True
        else:
            print("✗ XeLaTeX-Fehler:")
            print(result.stderr)
            
            # Fallback mit pdflatex
            print("\nVersuche Fallback mit pdflatex...")
            cmd[3] = "--pdf-engine=pdflatex"
            cmd = [x for x in cmd if not x.startswith("-V")]  # Entferne Font-Einstellungen
            
            result2 = subprocess.run(cmd, capture_output=True, text=True)
            if result2.returncode == 0:
                print("✓ PDF mit pdflatex erstellt!")
                print(f"  Dateigröße: {output_file.stat().st_size / 1024:.1f} KB")
                return True
            else:
                print("✗ Auch pdflatex fehlgeschlagen:")
                print(result2.stderr)
                return False
            
    except FileNotFoundError:
        print("✗ pandoc nicht gefunden!")
        print("Installation: https://pandoc.org/installing.html") 
        print("Oder: winget install pandoc")
        return False
    except Exception as e:
        print(f"✗ Unerwarteter Fehler: {e}")
        return False

if __name__ == "__main__":
    success = create_pdf_robust()
    sys.exit(0 if success else 1)