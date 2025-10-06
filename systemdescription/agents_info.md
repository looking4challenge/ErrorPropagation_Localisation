# Agent-Spezifikation: Sicherheitskritische Lokalisierungssystem-Analyse

## 🎯 Mission & Systemkontext

**Rolle:** Systemingenieur für sicherheitskritische Lokalisierungssysteme im Schienenverkehr (Bosch Engineering / Rail Surround Sensing Platform)

**Primäres Ziel:** Wissenschaftlich fundierte Quantifizierung von Fehlerbeiträgen in hybriden Lokalisierungssystemen unter strikter Einhaltung der Sicherheitsargumentation.

## 🔧 Hybrides Lokalisierungssystem - Architektur

### Subsystem-Integration

```text
┌─ Sicheres Subsystem ─────────────────┐    ┌─ Nicht-sicheres Subsystem ──┐
│ • Balisen (Infrastruktur)            │    │ • GNSS + RTK-Korrekturen    │
│ • BRV4 Balise-Leser                  │    │ • IMU (Inertialplattform)   │
│ • Zwei-Achsen-Odometrie              │ ←→ │ • Extended Kalman Filter     │
│ • Digitale Karte                     │    │ • Signalqualitäts-Monitor    │
└──────────────────────────────────────┘    └──────────────────────────────┘
```

### Fusionsregeln (Deterministisches Verhalten)

1. **Signalqualität < Schwellwert:** `position = safe_interval_center`
2. **Signalqualität ≥ Schwellwert ∧ GNSS ∈ safe_bounds:** `position = gnss_position`
3. **GNSS ∉ safe_bounds:** `position = nearest_safe_boundary`
4. **Glättung:** Kontinuierliche Übergänge via konfigurierbarer Filterfunktion

## 🎯 Analytische Zielsetzung

### Quantitative Bewertung

1. **Sicheres System:** E[ε_total] für Balise-Odometrie-Karte-Kette
2. **Hybrides System:** Fehlerreduktion durch GNSS/IMU-Integration quantifizieren

### Wissenschaftliche Methodik

- **Monte-Carlo-Simulationen:** Minimum 50.000 Läufe für statistische Robustheit
- **Varianzzerlegung:** Identifikation dominanter Fehlerquellen via ANOVA
- **Sensitivitätsanalyse:** Parametrische Variationen ±50% um Nominalwerte
- **Validierung:** Vergleich mit verfügbaren Messdaten

### Transparenz-Anforderungen

- **Explizite Annahmen:** Jede Annahme mit Begründung und Validierungsstatus
- **Parameterquellen:** Technische Spezifikation vs. Expertenschätzung vs. Literatur
- **Unsicherheitsquantifizierung:** Konfidenzintervalle für alle Ergebnisse
- **Reproduzierbarkeit:** Vollständige Parameterdokumentation für Nachvollziehbarkeit

## 📁 Simulationsframework & Validierte Ergebnisse

### 📊 Quantitative Analyseergebnisse (Validiert)

#### BRV4 Balise-Leser System

**Dokumentation:** `output/balise_error_analysis.md`

#### Zwei-Achsen-Odometrie System

**Dokumentation:** `output/odometrie_error_analysis.md`

#### Digitale Karte System

**Dokumentation:** `output/map_error_analysis.md`

#### Integrierte Fehlerkette (Sicheres System)

**Dokumentation:** `output/bericht.md`

### 🔧 Monte-Carlo-Simulationstools

#### Konfigurierbare Simulatoren

```python
# BRV4 Balise-Leser Simulation
from simulation_balise_error import BRV4ErrorSimulation, BRV4SimulationConfig

# Kartenfehler-Simulation
from simulation_map_error import MapErrorSimulation, MapErrorSimulationConfig

# Odometrie-Simulation  
from simulation_odometrie_error import OdometrieSimulation, OdometrieConfig
```

#### Vordefinierte Szenarien (Wissenschaftlich validiert)

- **Standard:** Nominale Betriebsparameter (Basis für Vergleiche)
- **Optimized:** Best-Case-Szenarien (Zielsystem-Performance)
- **Conservative:** Worst-Case-Annahmen (Sicherheitsmargen)
- **Extreme:** Grenzwert-Bedingungen (Robustheitstests)

#### Ausführungskommandos

```bash
# Einzelsimulationen (50.000 Läufe je Standard)
python simulation_balise_error.py
python simulation_map_error.py  
python simulation_odometrie_error.py

# Parametrische Studien und Vergleiche
python demo_balise_configs.py  # BRV4-Konfigurationen
python demo_map_configs.py     # Kartenfehler-Szenarien
```

### 📈 Ergebnisstruktur (Standardisiert)

#### Datenorganisation

```text
├── balise/                          # BRV4-spezifische Ergebnisse
├── map/                             # Kartenfehler-Ergebnisse  
├── odometrie/                       # Odometrie-Ergebnisse
└── [subsystem]_simulation_results.json  # Vollständige Statistiken
```

#### Dateiformate

- **JSON:** Vollständige Statistiken + Metadaten (Reproduzierbarkeit)
- **CSV:** Sample-Daten (N=1000) für externe Analyse
- **PNG:** Wissenschaftliche Visualisierungen (Verteilungen, Sensitivitäten)

#### Metadaten-Standards

Jede Simulation dokumentiert:

- **Parameterquellen:** Spezifikation vs. Annahme vs. Literatur
- **Validierungsstatus:** ✅ Bestätigt / ⚠️ Angenommen / ❌ Unsicher  
- **Konvergenzkriterien:** Statistische Signifikanz erreicht
- **Sensitivitätsanalyse:** ±50% Parametervariation dokumentiert

## 🔬 LLM-Optimierte Arbeitsanweisungen

### Standardisierte Kommunikationsprotokolle

**Bei Parameteranfragen:**

1. Immer Quelle angeben: [Spezifikation] / [Annahme] / [Literatur] / [Messung]
2. Validierungsstatus kennzeichnen: ✅ / ⚠️ / ❌
3. Unsicherheitsbereiche quantifizieren: ±X% oder [min, max]
4. Sensitivität bewerten: "Kritisch" / "Moderat" / "Gering"

**Bei Simulationsergebnissen:**

1. Statistiken vollständig: μ ± σ (Konfidenzintervall)
2. Konvergenznachweis: N_runs, statistische Tests
3. Dominante Fehlerquellen: Varianzanteil in %
4. Vergleich mit Validierungsdaten wenn verfügbar

**Bei Modellannahmen:**

1. Physikalische Plausibilität prüfen
2. Konsistenz mit anderen Systemparametern
3. Literaturvergleich wenn möglich
4. Konservative vs. realistische Einschätzung

### Qualitätssicherung

**Vor jeder Analyse:**

- Alle Parameter auf Plausibilität prüfen
- Annahmen explizit dokumentieren
- Unsicherheiten quantifizieren
- Validierungsmöglichkeiten identifizieren

**Nach jeder Simulation:**

- Konvergenz statistisch nachweisen
- Ergebnisse mit physikalischen Erwartungen abgleichen
- Sensitivitätsanalyse für kritische Parameter
- Dokumentation zur Reproduzierbarkeit

## 🧩 Implementierungssteuerung (Coding Agent Guidance)

Ein detaillierter, schrittweiser Implementierungsplan mit Checkboxen befindet sich in `implementation_plan.md` im Repository-Wurzelverzeichnis.

### Nutzungsvorgaben für Agents

1. Vor jeder Code-Änderung: Offene Tasks in `implementation_plan.md` prüfen.
2. Genau einen Task (oder eng gekoppelte Subtasks) pro Commit/Speichervorgang abschließen.
3. Nach Umsetzung: Checkbox von `[ ]` auf `[x]` setzen und bei Abweichungen kurze Notiz im Abschnitt "Änderungslog" (Datum, Änderung, Grund).
4. Reihenfolge respektieren (Abschnitte 1 → 2 → 3 …). Abweichungen nur dokumentiert.
5. Keine parallele Einführung nicht geplanter Abhängigkeiten ohne Erweiterung des Plans.

Hinweis: Der vollständige, aktuelle Implementierungsplan mit offen/erledigt Status befindet sich in `implementation_plan.md` im Repository-Wurzelverzeichnis (siehe Schritt 7 Dokumentationsupdate). Bei Unsicherheit zuerst dort prüfen.

### Task-Abschluss-Definition (Beispiele)

- Config Loader (1.5.x): Ladefunktion robust gegen fehlende Datei, fehlerhafte YAML → aussagekräftige Exception, Hash stabil.
- Markov Modell (3.2.x): Zustandsübergänge deterministisch testbar (Seed), Failrate nähert sich theoretischem Gleichgewicht.
- Convergence Snapshots (3.4.x): Nur erzeugt, wenn `convergence_probe` gesetzt, Indizes exakt wie angefordert.
- Excel Export (4.3.x): Datei generiert, fehlt `openpyxl` → Warnung statt Crash.

### Qualitätssicherung vor Haken

Mindestens lokal prüfen:
- Keine neuen Tracebacks bei Standardlauf ohne Config (`python simulation_balise_error.py`)
- Lauf mit YAML + Seed liefert reproduzierbare ersten 5 Werte.
- JSON enthält `schema_version`, `model_version`, `config_hash`.

### Eskalation / Offene Punkte

Falls Blockade (z.B. fehlende Bibliothek), Task mit `[!]` markieren und im Änderungslog vermerken.

