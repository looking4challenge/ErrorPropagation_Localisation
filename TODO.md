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
  - [ ] (Fix Follow-up) Lateral rule_based Anpassung für Outage (Fallback lateral_secure statt 0)
  - [x] CLI-Schalter --fusion-mode (rule_based|var_weight) hinzufügen
  - [x] Secure-Intervallbreite explizit berechnen (additive P99) und exportieren (secure_interval_metrics.csv)
  - [x] Quantifizierung Additive-P99 Überschätzung: Vergleich MC-Faltung vs. additive Summation (Bias %, ΔP99)
  - [x] Stress-Szenario Flags: --stress balise_tail / odo_residual / heavy_map implementieren
  - [x] Latenz Early-Detection Placeholder (wenn aktiviert) neutral validieren (ΔP95 <= 0.5 mm) -> sonst deaktiviert lassen (Export early_detection_eval.json)
  - [x] Plot secure_interval_growth (Zeit-/Distanzmodell Integration Basis 1s Cadence)
  - [x] Unit-Test: secure_interval additive Bias > 0 (neu geschrieben, Mehrfach-Replikation + Zeitreihenprüfung)
  - [ ] (NEU A) Asymmetrisches sicheres Intervall: Konzept ableiten (Speed-binning oder funktionale Skalierung) – Design-Dokument Abschnitt erstellen
  - [x] (NEU A) Implementierung Funktion `compute_secure_interval_bounds(secure_components, speeds, method="adaptive")` → quantilbasiert speed-bins
  - [x] (NEU D) Adaptive Aktualisierung: Intervallgrenzen in `simulate_time_series` alle `interval_update_cadence_s` (Default 1 s)
  - [x] (NEU B) Qualitätsheuristik: Nutzung unsafe wenn verfügbar & innerhalb [lower,upper]
  - [x] (NEU C) Zustandfulle 4-Regeln-Fusion: `RuleFusionState` + `rule_based_fusion_step` mit linearer Glättung
  - [x] (NEU C) Midpoint = 0.5*(lower+upper) implementiert
  - [x] (NEU A/D) Clamping für asymmetrische Grenzen (API vorbereitet)
  - [x] Integration: Zeitreihen-Sim nutzt zustandsvolle Step-Fusion longitudinal
  - [ ] Lateral Erweiterung: analoge Regeln mit eigener (vorerst symmetrischer) Intervallabschätzung (später asymmetrisch falls Datenbasis)
  - [x] Lateral Erweiterung: analoge Regeln (symmetrisch) optional via config `fusion.lateral_rule_based`
  - [x] Metrik-Export: Anteil Zeit in Modi (midpoint / unsafe / unsafe_clamped), Anzahl Transitionen, durchschnittliche Übergangsdauer → `results/fusion_mode_stats.csv` (Residence Approx via switch_rate)
  - [x] Metrik-Export: Anteil Zeit in Modi + Switch Rate → fusion_mode_stats.csv / fusion_switch_rate.csv
  - [x] Plot: Anteil Modi über Zeit (Stacked Area) → fusion_mode_share.png
  - [x] Plot: Intervallgrenzen Snapshot (asym. vorbereitet) → fused_time_interval_bounds.png
  - [x] Performance-Check: CLI `--perf` Runtime Vergleich adaptive vs legacy (CSV Export performance_fusion_runtime.csv). Overhead-Grenzprüfung noch offen.
  - [x] Fallback Konfiguration: Falls adaptive Quantile numerisch instabil (zu wenige Samples in Bin) → revert auf globale additive P99 Halbbreiten (Warnung ins Log)
  - [x] Tests: (1) Sprunggrößen-Grenze, (2) Clamping vorhanden, (3) Outage→Midpoint Blend, (4) Ausreißer→Clamped
    - [x] Teilimplementierung: Clamping, Asymmetrie Midpoint, Switch Count, Blend Monotonie (Basis) vorhanden (test_stateful_fusion.py)
  - [x] Test: Asymmetrie Greift – künstliche Skalierung upper=2*lower erzeugt erwartete verschobene Midpoints
  - [ ] decisions.log Einträge: A (Asymmetrie & Speed-abh.), B (Heuristik), C (linear blend), D (adaptive update cadence)
  - [ ] Dokumentation: Abschnitt „Adaptive asymmetrische sichere Intervallbestimmung“ (Formeln, Parameter, Limitierungen) im Bericht
  - [ ] CLI Erweiterung: `--interval-update-cadence-s` & `--fusion-stats` & `--no-adaptive-interval` (Fallback Flag)
  - [x] CLI Erweiterung umgesetzt (inkl. --export-interval-bounds)
  - [x] Config Erweiterung: `fusion: { interval: { adaptive: true, update_cadence_s: 1.0, quantile_low_pct: 1.0, quantile_high_pct: 99.0, min_bin_fraction: 0.05 } }`
  - [x] Robustheit: Handling leerer Geschwindigkeits-Bins → global quantiles fallback
  - [x] Logging: Warnungen bei >20% Bins fallback / <min_bin_fraction
  - [ ] Refactoring Alt: Entferne statische `rule_based_fusion` (epoch) nach Integration (oder markiere deprecated)
  - [ ] Technische Schuld: Parameterisierung blend_steps testbar (Expose via config + CLI override)
  - [ ] Optional: Exponentielle Glättungsvariante (α) evaluieren – nur dokumentieren, nicht aktivieren (Vergleich Stabilität)
  - [ ] Optional: Export Intervall-Bounds Zeitreihe (`secure_interval_bounds.csv`) für Audit

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
- [ ] Logging Anteil unsafe Nutzung (Prozentsatz Samples) + secure_only Baseline Kennzahl exportieren
- [ ] Optional: Unit-Test für Secure-Intervallbreite (monoton wachsend mit Distanz, obere Schranke Stress-Szenario)
- [ ] (NEU) Wartung adaptive Intervall: Regressionstest bei Änderungen an Sensorverteilungen (Snapshot quantile bias < 5%-Pkt Änderung)
- [ ] (NEU) Mode Share Drift Alarm: Warnung falls Anteil unsafe_clamped > definierter Schwellwert (z.B. 10%)

## Neue / Querschnittliche Aufgaben

- [x] Implementieren secure_interval Export
- [x] Zeitverlauf (W(d) vs. Distanz) – Plot figures/secure_interval_growth.png (Zeit-proxy)
- [ ] CLI Option --export-covariance für empirische Komponenten-Kovarianz (Validierung additive Annahme)
- [x] CLI Option --export-covariance für empirische Komponenten-Kovarianz (Validierung additive Annahme)
- [x] Prüf-Skript: additive_p99_bias.py (berechnet relative Überschätzung vs. Monte-Carlo quantile der Summe)
- [x] Konvergenz-Traces (RMSE/P95/P99/ES95) Export (--convergence)
- [ ] Early Detection Evaluierung (nur wenn Daten verfügbar) – separater Metrics-Block early_detection_eval.json
- [ ] Dokumentation Stress-Modi: heavy_tail_balise, wide_odo_residual, high_multipath_gnss
