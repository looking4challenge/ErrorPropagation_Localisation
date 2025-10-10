# Early-Detection Balise – Modell & Sensitivität (Entwurf)

Formel: \( e_{early} = d_{const} - v\, \Delta t_{adv} \), mit \( \Delta t_{adv} = \min(c_1 v, \text{cap}) \).

Parameter (Baseline model.yml):

- d_const_m = 0.10 m (Bad Weather: 0.08 m)
- c1_ms_per_mps = 0.5 ms/(m/s)
- cap_ms = 4.0 ms

Interpretation:

- Positiver Offset d_const modelliert systematischen Antennen-Vorversatz.
- Geschwindigkeitsterm reduziert den effektiven Vorlauf bei höheren Geschwindigkeiten (linear bis cap).

Varianzbeitrag (approx.):

- Berechnet durch Abschalten von d_const und Re-Evaluierung des secure/fused P95 (Proxy).
- Exportierte Kennzahlen: early_detection_p95_delta_m, early_detection_p95_rel_pct, early_detection_var_contrib_pct in fused_metrics.json.

Bewertungskriterium:

- Falls |early_detection_p95_rel_pct| < 1% ⇒ Beitrag als sekundär einstufen und im Hauptbericht nur tabellarisch aufführen.

Nächste Schritte:

- Validierung gegen reale Balisen-Triggerzeitdaten (sofern verfügbar) zur Kalibrierung von c1 und cap.
- Aufnahme in OAT Sensitivität (Parameter: d_const_m) – implementiert.
