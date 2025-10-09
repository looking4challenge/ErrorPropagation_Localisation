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
- [x] Lateral/2D Erweiterung (Feinschliff)
  - [x] Zeitreihen Grundgerüst (longitudinal, open mode)
  - [x] Modus-Vergleich (urban/tunnel) (statische Epochensamples)
  - [x] Lateral Fehlerpfad hinzugefügt (Balise/Map quer, vereinfachte Annahmen)
  - [x] Verbesserte 2D Fusion (separate Gewichtung longitudinal/lateral im Zeitmodell)
  - [x] Realistischere Lateral-Unsicherer Pfad (eigene GNSS Quer Noise/Bias Parametrisierung implementiert)
  - [x] Regelbasierte 4-Regeln-Fusion implementieren (Clamping + Blend) anstelle rein varianzgewichteter Surrogat-Fusion
  - [x] CLI-Schalter --fusion-mode (rule_based|var_weight) hinzufügen
  - [x] Secure-Intervallbreite explizit berechnen (additive P99) und exportieren (secure_interval_metrics.csv)
  - [x] Quantifizierung Additive-P99 Überschätzung: Vergleich MC-Faltung vs. additive Summation (Bias %, ΔP99)
  - [x] Stress-Szenario Flags: --stress balise_tail / odo_residual / heavy_map implementieren
  - [x] Latenz Early-Detection Placeholder (wenn aktiviert) neutral validieren (ΔP95 <= 0.5 mm) -> sonst deaktiviert lassen (Export early_detection_eval.json)
  - [x] Plot secure_interval_growth (Zeit-/Distanzmodell Integration Basis 1s Cadence)
  - [x] Unit-Test: secure_interval additive Bias > 0 (neu geschrieben, Mehrfach-Replikation + Zeitreihenprüfung)

## Phase 5 - Sensitivität & Validierung

- [x] OAT Sensitivität (Baseline Ranking, longitudinal RMSE)
- [x] OAT Erweiterung lateral/2D (ΔRMSE_lat, ΔRMSE_2d, ΔP95_2d)
- [x] Sobol (Longitudinal RMSE – Jansen Fallback, Basisgröße klein)
- [x] ES95 (Expected Shortfall 95%) Conditioning
- [ ] Validierung gegen Daten (falls vorhanden)
  - [ ] Quer/Längs Residuen getrennt (falls Daten 2D enthalten)
- [x] Additive vs. Joint P99 Sensitivität (Bias Ranking implementiert)
- [x] Konsolidierter Sensitivitätsbericht (inkl. Sobol & ΔES95) – Basis vorhanden, Erweiterung folgt
  - [ ] Sobol Verfeinerung (N_base erhöhen)
  - [ ] Erweiterung Sobol auf rmse_2d / p95_2d (Parameterliste ggf. ausdünnen)
  - [ ] Parameter-Subset für Stress Szenarien (Tail Gewicht w_tail, odo residual range, map interpolation weight) global analysieren
  - [ ] Dokumentation Sensitivitätsimplikationen: Top 5 Parameter → empfohlene Überwachungen / Kalibrierung
  - [ ] Integration OAT2D & Bias Sensitivität in Bericht (Tabellen + Kurzinterpretation)

## Phase 6 - Bericht

- [ ] Markdown Bericht erstellen
- [ ] Akzeptanzkriterien prüfen
  - [ ] 2D Kennzahlen (RMSE_2D, P95_2D) dokumentieren
  - [ ] Abschnitt Secure Intervall (Methodik additive P99 + Bias Quantifizierung)
  - [ ] Abschnitt Regelbasierte Fusion (4 Regeln + Sicherheitsgarantie Clamping) hinzufügen
  - [ ] Darstellung Additive vs. Joint P99 Vergleich (Tabelle + Prozentuale Überschätzung)
  - [ ] Stress-Szenario Ergebnisse (Kurzvergleich Baseline vs. Stress) aufnehmen
  - [ ] Reproduzierbarkeitssektion um Config-Hash & secure_interval settings erweitern

## Dauerhaft

- [ ] decisions.log pflegen
- [ ] Seeds & Reproduzierbarkeit sicherstellen
 - [ ] Konsistenz model.yml ↔ Systemübersicht prüfen bei jeder strukturellen Änderung (Automatische Checkliste)
 - [ ] Technische Schuld: Refactoring fuse_pair Nutzung entfernen wenn rule_based aktiv (Dead Code vermeiden)
 - [ ] Optional: Unit-Test für Secure-Intervallbreite (monoton wachsend mit Distanz, obere Schranke Stress-Szenario)

## Neue / Querschnittliche Aufgaben

- [x] Implementieren secure_interval Export
- [x] Zeitverlauf (W(d) vs. Distanz) – Plot figures/secure_interval_growth.png (Zeit-proxy)
- [ ] CLI Option --export-covariance für empirische Komponenten-Kovarianz (Validierung additive Annahme)
- [ ] Prüf-Skript: additive_p99_bias.py (berechnet relative Überschätzung vs. Monte-Carlo quantile der Summe)
- [ ] Early Detection Evaluierung (nur wenn Daten verfügbar) – separater Metrics-Block early_detection_eval.json
- [ ] Dokumentation Stress-Modi: heavy_tail_balise, wide_odo_residual, high_multipath_gnss
