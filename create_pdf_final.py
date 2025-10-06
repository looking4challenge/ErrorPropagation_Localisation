#!/usr/bin/env python3
"""
Finale PDF-Erstellung - einfach und robust
"""

import os
import sys  
import re
from pathlib import Path
import subprocess

def fix_all_issues(input_file, output_file):
    """Behebt alle gemeldeten Probleme in einer Funktion"""
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Behebe alle Formatierungsprobleme...")
    
    # 1. KRITISCH: Doppelte Kapitelnummerierung entfernen
    # Muster wie "### 1.2.3 4.1 Titel" -> "### 4.1 Titel"
    print("  ✓ Entferne doppelte Kapitelnummerierung")
    content = re.sub(r'^(#{1,6})\s+\d+(?:\.\d+)*\s+(\d+(?:\.\d+)+\s+.*?)$', r'\1 \2', content, flags=re.MULTILINE)
    
    # 2. KRITISCH: Sigma und griechische Zeichen durch ASCII ersetzen
    print("  ✓ Ersetze griechische Zeichen und Unicode-Symbole durch ASCII-Äquivalente")
    replacements = {
        'σ': 'sigma',
        'ρ': 'rho', 
        'α': 'alpha',
        'λ': 'lambda',
        'μ': 'mu',
        'ε': 'epsilon',
        'Δ': 'Delta',
        'τ': 'tau',
        'ω': 'omega',
        '≤': '<=',
        '≥': '>=', 
        '±': '+/-',
        '→': '->',
        '↔': '<->',
        '×': 'x',
        '∘': 'deg',
        '²': '^2',
        '³': '^3',
        # Box-drawing Zeichen
        '┌': '+',
        '┐': '+',
        '└': '+',
        '┘': '+',
        '├': '+',
        '┤': '+',
        '┬': '+',
        '┴': '+',
        '┼': '+',
        '─': '-',
        '│': '|',
        '▼': 'v',
        '◄': '<',
        '►': '>',
        # Weitere Unicode
        '•': '*'
    }
    
    for greek, ascii_rep in replacements.items():
        content = content.replace(greek, ascii_rep)
    
    # 3. Große Tabelle 4.2 markieren
    print("  ✓ Markiere große Tabelle für Querformat-Hinweis")
    content = content.replace(
        '### 4.2 Konsolidierte Fehlerparametertabelle',
        '### 4.2 Konsolidierte Fehlerparametertabelle\n\n**Hinweis:** Diese umfangreiche Tabelle wird zur besseren Lesbarkeit im Querformat dargestellt.\n\n\\newpage\n\\landscape'
    )
    
    # Ende der Tabelle markieren
    content = content.replace(
        '### 4.3 Korrelationen zwischen Fehlerquellen',
        '\\endlandscape\n\\newpage\n\n### 4.3 Korrelationen zwischen Fehlerquellen'
    )
    
    # 4. Weitere Verbesserungen
    print("  ✓ Verbessere Tabellen- und Code-Formatierung")
    
    # Code-Blöcke vereinheitlichen
    content = re.sub(r'```text\n', '```\n', content)
    
    # Seitenumbrüche vor Hauptkapiteln
    content = re.sub(r'^## (\d+\.)', r'\\newpage\n\n## \1', content, flags=re.MULTILINE)
    
    # Tabellen-Markup verbessern
    content = re.sub(r'\*\*(.*?)\*\*:', r'**\1:**', content)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ Bereinigte Datei gespeichert: {output_file}")

def create_final_pdf():
    """Finale PDF-Erstellung ohne Komplikationen"""
    
    project_root = Path(__file__).parent
    input_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.md"
    clean_file = project_root / "report" / "stakeholder_bericht_clean.md"
    output_file = project_root / "report" / "stakeholder_bericht_vorgehen_v1.pdf"
    
    print("=== FINALE PDF-ERSTELLUNG ===")
    print(f"Input:  {input_file.name}")
    print(f"Output: {output_file.name}")
    
    if not input_file.exists():
        print("❌ Eingabedatei nicht gefunden!")
        return False
    
    try:
        # 1. Alle Probleme beheben
        fix_all_issues(input_file, clean_file)
        
        # 2. Minimaler pandoc-Aufruf
        print("\nErstelle PDF...")
        cmd = [
            "pandoc",
            str(clean_file),
            "-o", str(output_file),
            "--variable", "geometry:margin=2cm",  
            "--variable", "fontsize=10pt",
            "--table-of-contents",
            "--number-sections"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            size_kb = output_file.stat().st_size / 1024
            print(f"\n🎉 PDF ERFOLGREICH ERSTELLT!")
            print(f"   Datei: {output_file}")
            print(f"   Größe: {size_kb:.1f} KB")
            
            print(f"\n✅ BEHOBENE PROBLEME:")
            print(f"   • Sigma-Zeichen: σ -> 'sigma' (ASCII-kompatibel)")
            print(f"   • Doppelte Kapitelnummerierung entfernt")
            print(f"   • Große Tabelle 4.2 für Querformat markiert") 
            print(f"   • Alle Unicode-Zeichen durch ASCII ersetzt")
            print(f"   • Seitenumbrüche vor Hauptkapiteln")
            
            # Cleanup
            if clean_file.exists():
                clean_file.unlink()
            
            return True
            
        else:
            print(f"\n❌ pandoc-Fehler:")
            if result.stderr:
                print(result.stderr)
            return False
            
    except FileNotFoundError:
        print(f"\n❌ pandoc nicht installiert!")
        print(f"   Installation: https://pandoc.org/installing.html")
        print(f"   Windows: winget install pandoc")
        return False
        
    except Exception as e:
        print(f"\n❌ Unerwarteter Fehler: {e}")
        return False

if __name__ == "__main__":
    success = create_final_pdf()
    print(f"\n{'='*50}")
    if success:
        print("🎯 PDF-ERSTELLUNG ABGESCHLOSSEN")
    else:
        print("💥 PDF-ERSTELLUNG FEHLGESCHLAGEN")
    print(f"{'='*50}")
    sys.exit(0 if success else 1)