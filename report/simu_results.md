# Simulationsvergleich (4 Szenarien)

Datum: 2025-10-09 (UTC)  
Ausführung: `run_sim.py` mit 10.000 Samples je Szenario, Rule-Based Fusion, Zeitreihen + Konvergenz aktiviert, Roh-Samples gespeichert.

## Szenarien

1. Regular (Baseline)
2. Bad Weather (erschwerte Bedingungen: höhere Varianzen, stärkere Tails, mehr GNSS-Outage)
3. No GNSS (GNSS komplett ausgefallen; Fusionspfad entspricht im Wesentlichen dem sicheren Pfad)
4. Odo 5cm (stark erhöhte Umfangs-/Driftunsicherheit Odometrie)

## Kernergebnisse (qualitativ)

- Bad Weather verschlechtert RMSE & P95 sowohl für sichere Komponenten (Balise, Map leicht) als auch stark für unsicheren GNSS/IMU-Pfad; Fusion reagiert durch Interval-Handling mit häufigerem Midpoint.
- No GNSS eliminiert Nutzen des unsicheren Pfads; Fused ≈ Secure; Varianzreduktion durch Fusion entfällt.
- Odo 5cm hebt additive P99 und RMSE/P95 des Secure-Pfades moderat an; Auswirkungen auf Fusion geringer als Bad Weather, aber stärker fokussiert auf Langfehler (drift).
- Additives P99-Intervall bleibt konservativ; Bias (additiv vs joint) bleibt im niedrigen zweistelligen Prozentbereich und variiert zwischen Szenarien.

## Validierungsschritte

- Metrikdateien: `results/<scenario>/metrics_*.json` sowie aggregiert `metrics_all.csv` geprüft (Existenz & plausible Größenordnungen: RMSE << P95 < P99, kein NaN).
- Konvergenz: Dateien `convergence_quantiles.csv`, `convergence_rmse.csv` vorhanden; Stichprobengröße (10k) zeigt abgeflachte Traces gegen Ende → Konvergenz ausreichend für P95/ RMSE grob gewährleistet.
- Zeitreihen: `time_series_metrics.csv` vorhanden mit erwarteten Spalten (`rmse_long`, `p95_long`, Varianzen). In No-GNSS Szenario geringere Var_unsafe Werte (GNSS tot) → erwartungskonform.
- Additive Intervallannahme: Unterschied additive vs joint P99 dokumentiert in `metrics_fused.json` Feldern `secure_interval_p99_additive` & `secure_interval_p99_joint`.

## Beobachtete Muster (hochlevel)

- Bad Weather: Erhöhte Tail-Indikatoren (größere additive P99). Erwartete Verschärfung durch multipath_tail und GNSS noise Parameter.
- No GNSS: Fused-Verteilung enger als Bad Weather, jedoch etwas breiter als Regular Secure allein, da IMU Bias beiträgt.
- Odo 5cm: Leichte Verschiebung der Secure-Distribution; GNSS bleibt unverändert → Fusion gleicht stärker über GNSS aus.

## Quantitative Kernmetriken

Quelle: `results/metrics_all.csv` (n = 10.000 je Szenario; Werte in m, 3 signifikante Stellen gerundet). Leere Einträge bedeuten: Metrik für diese Komponente (noch) nicht bestimmt/irrelevant.

| Komponente | Mean | Std | RMSE | P50 | P90 | P95 | P99 | RMSE_lat | P95_lat | RMSE_2D | P95_2D |
|-----------|------|------|------|-----|-----|-----|-----|----------|---------|---------|--------|
| Balise | 0.106 | 0.0591 | 0.121 | 0.104 | 0.186 | 0.207 | 0.244 |  |  |  |  |
| Map | 0.00781 | 0.0235 | 0.0247 | 0.00611 | 0.0387 | 0.0498 | 0.0693 |  |  |  |  |
| Odometry (long drift) | 0.00455 | 0.747 | 0.747 | 0.00524 | 0.953 | 1.24 | 1.78 |  |  |  |  |
| IMU | 0.00282 | 0.250 | 0.250 | 0.00373 | 0.320 | 0.407 | 0.579 |  |  |  |  |
| GNSS Open | 0.00472 | 0.386 | 0.386 | 0.00542 | 0.499 | 0.645 | 0.894 |  |  |  |  |
| GNSS Urban | 0.0521 | 0.961 | 0.962 | 0.0509 | 1.27 | 1.63 | 2.33 |  |  |  |  |
| GNSS Tunnel | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |  |  |  |
| Secure Pfad | 0.118 | 0.750 | 0.759 | 0.122 | 1.07 | 1.36 | 1.91 |  |  |  |  |
| Unsafe Pfad | 0.00225 | 0.466 | 0.466 | ~0.000 | 0.610 | 0.765 | 1.05 |  |  |  |  |
| Fused | 0.0345 | 0.396 | 0.397 | 0.0337 | 0.535 | 0.683 | 0.953 | 0.0358 | 0.0590 | 0.399 | 0.782 |

Hinweise:
1. Fused vs Secure: RMSE-Reduktion ≈ 47.6% (0.759 → 0.397); P95-Reduktion ≈ 49.7% (1.36 → 0.683) trotz riskanter Pfadanteile.
2. Secure Pfad dominiert die Langtail-Metriken (drift + additive Intervallkonstruktion) – sichtbar an P99.
3. GNSS Urban deutlich tail-lastiger als Open (P99 Faktor ~2.6 vs Open). Tunnel=0 (vollständige Ausblendung / Outage-Modell) → stützt Erwartung „kein Beitrag“.
4. Odometry/IMU zeigen erwartete Relation RMSE ≈ Std (Bias vernachlässigbar klein in diesen Läufen).

### 2D / Lateral Befund
Aktuell nur für `fused` erhoben: RMSE_lateral 0.0358 m (P95_lateral 0.0590 m). Verhältnis lateral zu longitudinal-RMSE_fused ≈ 0.0358 / 0.397 ≈ 9.0% → Lateralfehler deutlich kleiner; dominanter Unsicherheitsbeitrag ist longitudinal (drift + GNSS range noise). 2D-RMSE (0.399 m) liegt nur gering über longitudinal (0.397 m) → lateraler Beitrag nahezu orthogonal & klein.

## Sensitivitätsanalyse

### One-At-A-Time (OAT) – RMSE (longitudinal Proxy)
Quelle: `results/sensitivity_oat.csv`. Ranking nach |rel_change| (größerer Betrag einer Seite):

| Parameter (variiert ±Δ%) | Baseline RMSE | RMSE− | RMSE+ | rel− % | rel+ % | stärkster Effekt % |
|--------------------------|---------------|-------|-------|--------|--------|---------------------|
| Balise Latenz Std | 0.881 | 0.903 | 0.899 | +2.53 | +2.14 | 2.53 |
| IMU Accel Bias Std | 0.881 | 0.890 | 0.895 | +1.06 | +1.65 | 1.65 |
| GNSS Bias Lat Std | 0.881 | 0.873 | 0.891 | -0.81 | +1.14 | 1.14 |
| Odo Drift / km | 0.881 | 0.890 | 0.889 | +1.09 | +0.94 | 1.09 |
| GNSS Noise Std | 0.881 | 0.873 | 0.887 | -0.86 | +0.76 | 0.86 |

Interpretation: Kurzfristig (unter der gewählten Δ) wirken Balise-Latenz und IMU Accel Bias am stärksten (jedoch insgesamt geringe Elastizitäten <3%). GNSS Noise zeigt asymmetrischen Effekt (Rauschen senken hilft etwas stärker als Erhöhung schadet).

### Sobol (Total-Order) – RMSE 2D
Quelle: `results/sensitivity_sobol_rmse_2d.csv` (Jansen-Fallback; S1 teils negativ wegen Schätzrauschen, Total-Order ST entscheidend):

| Parameter | ST (Total) | Rang |
|-----------|-----------:|-----:|
| GNSS Bias Lat Std | 1.157 | 1 |
| Odo Drift / km | 0.948 | 2 |
| IMU Accel Bias Std | 0.913 | 3 |
| GNSS Bias Std | 0.902 | 4 |
| Map Long Ref Error Std | 0.850 | 5 |
| Balise Latenz Std | 0.809 | 6 |
| GNSS Noise Lat Std | 0.702 | 7 |
| Balise Multipath Tail Cap | 0.700 | 8 |
| GNSS Noise Std | 0.561 | 9 |

ST>1 bei erstem Parameter deutet auf Interaktionseffekte und/oder Varianzaufblähung (Estimator + Varianzsharing) – weitere Replikate könnten Konfidenz verengen.

### Quantile-Sensitivität (P95 Fused)
Quelle: `results/sensitivity_quantile_p95.csv` (Low/High Szenen-Anteile je 20%).

| Quelle | Baseline P95 | Low P95 | High P95 | Δ (High-Low) | Anteil stärkster Effekt |
|--------|--------------|---------|----------|--------------|-------------------------|
| GNSS Open | 0.683 | 0.139 | 0.943 | 0.804 | dominant |
| Odometry | 0.683 | 0.335 | 0.929 | 0.593 | hoch |
| IMU | 0.683 | 0.383 | 0.892 | 0.509 | relevant |
| Balise | 0.683 | 0.643 | 0.711 | 0.068 | gering |
| Map | 0.683 | 0.663 | 0.679 | 0.016 | vernachlässigbar |

Interpretation: Extreme (Tail) des Fused-P95 klar GNSS-getrieben, gefolgt von Odometrie-Drift (Langdrift) und IMU Bias. Balise & Map wirken nahezu deterministisch im Vergleich.

### Konsolidierte Erkenntnisse Sensitivität
1. RMSE-Elastizitäten (lokal) klein → System relativ robust auf moderate Parameteränderungen.
2. Tails / hohe Quantile dominieren Risikobetrachtung und werden stark durch GNSS- und Drift-bezogene Parameter bestimmt.
3. Interaktionen: Hohe ST-Werte weisen auf Nichtlinearitäten im Fusions-Proxy (z.B. Schaltlogik / Intervallauswahl) hin.

## Aktualisierte Limitationen & Nächste Schritte

- Empirische Korrelations-/Kovarianz-Matrix noch nicht exportiert (Flag `--export-covariance` offen) → Validierung Copula-Annahmen steht aus.
- 2D/Lateral Metriken nur für `fused` erhoben – Erweiterung auf andere Komponenten möglich (falls Rohdaten vorhanden).
- Negativ-S1 Sobol Indizes deuten auf Monte-Carlo Rauschen; zusätzliche Replikate oder Saltelli-Sampling zur Stabilisierung empfohlen.
- Automatisierte Generierung reproduzierbarer Tabellen & Figures sollte als Skript formalisiert werden (derzeit manuell aus CSV gelesen).

Abgeschlossene Punkte (vorher Limitationen): Tabellen extrahiert; Sensitivitäten (OAT, Sobol, Quantile) integriert; 2D Kennzahlen interpretiert.
## Additive vs. Joint P99 Bias (Secure Intervall)

Automatisierte Exportdatei: `results/secure_interval_metrics.csv` (bei Aufruf mit `--export-secure-interval`).

| Größe | Wert |
|-------|------|
| Additive P99 Summe (Balise+Odo+Map) | siehe metrics_fused.json Feld `secure_interval_p99_additive` |
| Joint P99 Secure Pfad | `secure_interval_p99_joint` |
| Überschätzungs-Bias % | `secure_interval_additive_bias_pct` |

Interpretation: Additive Summation bleibt konservativ (Bias > 0). Sensitivitätsanalyse (siehe `sensitivity_p99_bias_table.md`) zeigt, dass Parameter, die Varianz und/oder Tail einzelner sicheren Komponenten erhöhen (z.B. Balise Latenz-Std, Odo Drift), den Bias nur moderat verschieben – Haupttreiber sind stark skalierende Komponenten mit subadditiven Korrelationen.

## Automatisierungs-Hinweis

Die Tabellen in diesem Dokument können nun reproduzierbar via Skript erzeugt werden:
`python generate_tables.py --results results --report report`

Output-Dateien:
- `report/metrics_table.md`
- `report/sensitivity_oat_table.md`
- `report/sensitivity_sobol_table.md`
- `report/sensitivity_quantile_table.md`
- `report/sensitivity_p99_bias_table.md`

Integration in den Bericht kann künftig über Platzhalter/Anker erfolgen (TODO).

## Empfehlung

- Für formalen Bericht numerische Kernmetriken extrahieren und tabellieren.
- Bad-Weather Parameteranpassungen in Risikomatrix (Tail vs. Grundrauschen) differenziert darstellen.
- Erwägung zusätzlicher Läufe mit aktivierter `--oat` für Regular & Bad Weather zur quantitativen Attribution.

---
Automatisch generiert.
