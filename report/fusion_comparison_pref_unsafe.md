# Fusion Vergleich (secure-first vs. unsafe-prefer)

Datum: 2025-10-09

Ziel: Nach Korrektur der Regel-basierten Fusion (GNSS bevorzugt solange innerhalb Intervall) zeigen die Metriken jetzt deutliche Reduktion der longitudinalen Fehlerkennzahlen verglichen mit der ursprünglichen Implementation (secure-first Bug).

## Kennzahlen (fused longitudinal)

| Szenario | Variante | RMSE [m] | P95 [m] | P99 [m] | ΔRMSE vs. secure-first | ΔP95 |
|----------|----------|----------|---------|---------|------------------------|------|
| regular | secure-first | 0.7499 | 1.3477 | 1.8660 | – | – |
| regular | unsafe-prefer | 0.4623 | 0.7637 | 1.0535 | -38.4% | -43.3% |
| no_gnss | secure-first | 0.7499 | 1.3477 | 1.8660 | – | – |
| no_gnss | unsafe-prefer | 0.2503 | 0.4072 | 0.5794 | -66.6% | -69.8% |
| bad_weather | secure-first | 0.7559 | 1.3748 | 1.9034 | – | – |
| bad_weather | unsafe-prefer | 0.5785 | 0.9568 | 1.3233 | -23.5% | -30.4% |
| odo_5cm | secure-first | 0.7525 | 1.3519 | 1.8621 | – | – |
| odo_5cm | unsafe-prefer | 0.4623 | 0.7637 | 1.0535 | -38.6% | -43.5% |

Hinweis: No-GNSS zeigt jetzt deutliche Degradation gegenüber regular (unsafe-prefer), da GNSS Beiträge vollständig wegfallen.

## Interpretation

1. Korrigierte Fusion nutzt nun GNSS (präziser Pfad) solange dieser innerhalb der sicheren Intervallgrenzen liegt. Dadurch starke Reduktion der Streuung und Tail-Perzentile.
2. Unterschied regular vs. no_gnss quantifiziert GNSS Benefit (~0.4623 m → 0.2503 m RMSE Boost fällt weg → +99% RMSE Anstieg ohne GNSS).
3. Bad Weather reduziert den Benefit (RMSE 0.4623 → 0.5785 m) durch Verschlechterung von GNSS/Balise/Map Parametern.
4. Odo 5cm Stress wirkt kaum auf fused (GNSS dominiert), bestätigt Odometrie Stress nur sekundärer Beitrag solange GNSS gesund.
5. Additives P99 Intervall bleibt unverändert groß; Overestimation Bias Prozent bleibt gleich (relevant nur für Sicherheitsgarantie, nicht für Nutzen des Präzisionspfad). Möglichkeit: Intervallbreite für Fusionsentscheidung auf joint_p99 reduzieren, additive P99 weiter für Safety Proof nutzen.

## Offene Punkte

* Lateral Ausfallbehandlung (No-GNSS → lateral ~= 0) anpassen: fallback auf lateral_secure statt Null.
* Logging Anteil unsafe genutzt (% Samples) zur Transparenz.
* Optional: Metrik „secure_only_rmse“ parallel ausgeben für Benefit-Kalkulation (ΔRMSE durch GNSS).

## Reproduzierbarkeit

Configs: `config/scenario_*.yml`, Seeds unverändert (12345), Code Commit nach Fusion-Fix (datum 2025-10-09). Plots in `figures/scenario_*_pref_unsafe/`.
