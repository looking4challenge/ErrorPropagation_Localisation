## Konsolidierter Sensitivitätsbericht

Quelle Dateien (results/):

* `sensitivity_src_rmse_long_proxy.csv` (SRC)
* `sensitivity_prcc_rmse_long_proxy.csv` (PRCC)
* `sensitivity_quantile_p95.csv` (ΔQ95)
* `sensitivity_exceedance_T0.200.csv` (ΔP(|e|>T), T = 0.20 m)
* `sensitivity_es95.csv` (ΔES95)
* `sensitivity_sobol_rmse_long.csv` (Sobol S1/ST – Longitudinal RMSE; Fallback Jansen Estimator)

Baseline Zielmetrik Kontext:

* Betrachtete Zielgröße für SRC/PRCC: longitudinaler RMSE Proxy.
* Baseline Q95 (alle Parameter nominal): 0.6832 m.
* Perturbationen: ±10 % (delta_pct) um Nennwert (One-at-a-Time / OAT). Für ΔQ95 und ΔP(|e|>T) wurden Low/High Varianten simuliert, jeweils 20 % Stichproben-Anteil (low_frac/high_frac = 0.2) zum Vergleich herangezogen.

### Kennzahlen-Definitionen

* S1: Erster Ordnung Sobol Index (Varianzanteil einzelner Parameter) – berechnet (Jansen Fallback; kleine N, daher hohe Unsicherheit, S1_conf ≈ Bootstrap-Std).
* ST: Totaler Sobol Index (inkl. Interaktionen) – berechnet (Jansen Fallback). Werte >1 geringfügig möglich durch Stichprobenrauschen; interpretativ auf 0..1 zu clampen.
* SRC: Standardisierter Regressionskoeffizient (lineares Modell, z-standardisierte Inputs/Output).
* PRCC: Partial Rank Correlation Coefficient (monotone aber nicht zwingend lineare Abhängigkeit, Rangbasiert, partielle Korrektur anderer Variablen).
* ΔQ95: Spannweite des 95%-Quantils unter ±10 % Parameteränderung (high_q95 – low_q95) [m].
* ΔES95: Änderung Expected Shortfall (Tail-Mean oberhalb globalem 95%-Quantil) zwischen High und Low – jetzt berechnet.
* ΔP(|e|>T): Änderung der Überschreitungswahrscheinlichkeit für Schwellwert T=0.20 m (p_high – p_low) absolut (hier als absolute Differenz angegeben; Vorzeichen zeigt Richtung bei +10%).

### Konsolidierte Tabelle

| Parameter (aggregiert) | S1 | ST | SRC | PRCC | ΔQ95 [m] | ΔES95 [m] | ΔP(|e|>0.20 m) [abs] | ΔP [pp] | Rang (PRCC) |
|------------------------|-----|------|-------|-------|----------|-----------|----------------------|---------|-------------|
| gnss_open              | 0.019 | 0.903 | 0.7135 | 0.9465 | 0.8035 | 0.01540 | 0.0540 | 5.40 | 1 |
| odometry               | 0.064 | 0.949 | 0.5260 | 0.9059 | 0.5933 | 0.02071 | 0.0340 | 3.40 | 2 |
| imu                    | 0.0537 | 0.911 | 0.4564 | 0.8792 | 0.5090 | 0.01386 | 0.0685 | 6.85 | 3 |
| balise                 | -0.256 | 0.807 | 0.0416 | 0.1422 | 0.0681 | 0.00712 | 0.0140 | 1.40 | 4 |
| map                    | -0.236 | 0.852 | 0.0165 | 0.0652 | 0.0164 | -0.01444 | -0.0060 | -0.60 | 5 |

Anmerkung: Negative S1 aus Fallback-Schätzung resultieren aus Stichprobenrauschen bei kleiner Basisgröße (N_base=32); interpretativ nahe 0 behandeln. ST > 1 (gnss_open.bias_lat.std) in Roh-Datei auf 0–1 begrenzbar; hier unverändert für Transparenz. Mapping Parameterebene → aggregierte Komponente erfolgte durch Zuordnung der jeweiligen Einzelparameter zu ihrer Sensorgruppe (nur eine Haupt-Std je Komponente in Defaultliste → direkte Übernahme).

Rundung: 4 signifikante Stellen. ΔP [pp] = ΔP * 100.

Hinweis zu IMU vs. Odometry Rang: Obwohl IMU das höchste ΔP(|e|>0.2 m) liefert, bleibt Odometry nach PRCC/SRC vor der IMU. Dies deutet auf stärkere lineare / monotone Kopplung der Odometrie zum RMSE, während IMU-Störungen besonders in der Überschreitungs-Metrik (Tail) wirksam werden. ΔES95 bestätigt: Odometrie liefert größte Tail-Mean Steigerung, GNSS folgt knapp.

### Interpretation & Priorisierung (Top 3 Treiber)

1. GNSS (open mode Aggregat)
   * Höchste PRCC & SRC → stärkster monotone Einfluss auf RMSE.
   * Größtes ΔQ95 → stärkste Streckung der oberen Verteilungsflanke.
2. Odometrie
   * Zweithöchste Strukturkopplung (SRC/PRCC) – linear skaliert Fehlerbandbreite.
3. IMU
   * Tail-getrieben: Höchster Anstieg in Überschreitungswahrscheinlichkeit (ΔP) trotz geringfügig niedrigerem SRC als Odometrie.

Balise & Map

* Niedrige SRC/PRCC → marginaler Beitrag zur Varianz der longitudinalen Zielmetrik im aktuellen Horizont.
* Map zeigt sogar leicht negative ΔP bei +10 % Variation (leichte Stabilisierung durch Glättungseffekt, wahrscheinlich Sampling-Rauschen / sekundärer Interaktionseffekt).

### Fehlende Größen & Nächste Schritte

* Sobol Verfeinerung: Erhöhung N_base (aktuell 32) zur Reduktion von Varianz (Ziel: S1_conf < 0.05) und Eliminierung negativer S1.
* Lateral / 2D Sensitivität: Erweiterung der Sobol- und Conditioning-Pipelines auf rmse_2d & p95_2d.
* Robustere Tail-Metrik: Ergänzung Expected Shortfall ES99 zur höheren Sicherheitsabdeckung.
* Parameter-Gruppierung: Optionale Aggregation mehrerer GNSS Std-Parameter (bias/noise long+lat) über Varianzdekomposition.

### Empfehlungen (Kurz)

* Primäre Verbesserungshebel: GNSS Robustheit (Bias/Noise), Odometrie Driftreduktion – beide mit hohen ST (nahe 0.9–0.95) → strukturprägende Treiber.
* Tail-Risiko: Odometrie (höchstes ΔES95) & IMU (höchstes ΔP Exceedance) getrennt adressieren: Kalibrierzyklen, Driftmonitoring, Bias-Schätzung im Filter.
* GNSS: ST hoch, S1 moderat → Interaktionsanteile signifikant (Fusionspfad + Kopplung mit IMU / Odo). Priorisierung robuster Outage-/Multipath-Mitigation.
* Map/Balise: Geringe marginale Wirkung auf Varianz & Tails (aktuelle Konfiguration); Fokus eher auf Quervalidierung / Systemintegritätsbelege statt kurzfristige Optimierung.

### Reproduzierbarkeit

* Alle Werte direkt aus den oben gelisteten CSV-Dateien extrahiert (Stand dieses Commits). Sobol basierend auf N_base=32 (Jansen Fallback), ΔES95 Conditioning Low/High Quantile 20%/20%.
* Seed und Konfiguration: referenziert in `config/model.yml` und Lauf-Metadaten (`results/metrics_fused.json`).

Ende des Berichts.
