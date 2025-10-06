# TODO

## Phase 1 - Interview & Workspace Scan

- [x] Betriebsprofil vom Nutzer erheben
- [x] Sensorparameter verifizieren/ergänzen
- [x] Fusionsansatz bestätigen
- [ ] Validierungsdaten lokalisieren & Schema erfassen
- [x] Verteilungs- und Korrelationsannahmen validieren (methodisch)

## Phase 2 - Konfiguration finalisieren

- [x] `config/model.yml` aktualisieren
- [x] Korrelationstest-Skript implementieren

## Phase 3 - Code Skeleton & Tests

- [x] Module anlegen (config, distributions, sim_sensors, fusion, metrics)
- [x] Module sensitivity, plots erstellen
- [x] CLI `run_sim.py`
- [x] PyTest Grundgerüst
- [x] Test für Korrelationen
- [x] Test für GNSS Noise Sensitivität

## Phase 4 - Simulation & Auswertung

- [x] Monte-Carlo Ausführung (run_sim erweitert)
- [x] Metriken berechnen & speichern (JSON + CSV)
- [x] Plots generieren (PDF/CDF/QQ + Komponenten PDFs)
- [x] Zeitreihen / Modus-Vergleich (Grundgerüst + lateral/2D Metriken integriert)
- [ ] Lateral/2D Erweiterung (Feinschliff)
  - [x] Zeitreihen Grundgerüst (longitudinal, open mode)
  - [x] Modus-Vergleich (urban/tunnel) (statische Epochensamples)
  - [x] Lateral Fehlerpfad hinzugefügt (Balise/Map quer, vereinfachte Annahmen)
  - [x] Verbesserte 2D Fusion (separate Gewichtung longitudinal/lateral im Zeitmodell)
  - [ ] Realistischere Lateral-Unsicherer Pfad (eigene GNSS Quer Noise/Bias Parametrisierung statt Kopie)

## Phase 5 - Sensitivität & Validierung

- [ ] OAT Sensitivität
- [ ] Sobol optional
- [ ] Validierung gegen Daten (falls vorhanden)
  - [ ] Quer/Längs Residuen getrennt (falls Daten 2D enthalten)

## Phase 6 - Bericht

- [ ] Markdown Bericht erstellen
- [ ] Akzeptanzkriterien prüfen
  - [ ] 2D Kennzahlen (RMSE_2D, P95_2D) dokumentieren

## Dauerhaft

- [ ] decisions.log pflegen
- [ ] Seeds & Reproduzierbarkeit sicherstellen
