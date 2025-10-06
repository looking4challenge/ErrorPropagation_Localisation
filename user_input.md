Hier ein fokussiertes, priorisiertes Paket zusätzlicher Sensitivitätsmetriken – jeweils mit Zweck, Mehrwert gegenüber deiner bestehenden OAT-Analyse und praktischen Implementationshinweisen für euren Monte‑Carlo / SIL1 Kontext.

## Ausgangsbasis
Aktuell vorhanden: OAT (±Δ%) auf longitudinalem RMSE. Damit bekommst du lokale lineare Effekte um den Nominalpunkt, aber:
- Keine Interaktionen (Parameter-Kombinationen)
- Keine Aussage zur Dominanz für andere Zielgrößen (P95, lateral, 2D, Zeitpfad)
- Kein Fokus auf Tails (Sicherheitsrelevant: P99 oder spezifizierte Schwellenüberschreitungen)

## Priorisierte Empfehlungen (Staffel 1 – Hohes Nutzen/Kosten-Verhältnis)

1. Sobol First Order (S_i) + Total Order (S_Ti) für RMSE_long, RMSE_2D, P95_long  
   Warum: Liefert additive vs. interaktive Beiträge zur Varianz. Besonders wichtig um zu sehen, ob z. B. GNSS Noise nur über Interaktionen (mit Balise-Latenz / Map) wirkt.  
   Nutzen: Identifiziert, ob weitere Modellvereinfachungen (Fixieren von Parametern) gerechtfertigt sind.  
   Aufwand: Moderat (SALib vorhanden). Sampling ~ O(k·(2N+2)) bei Saltelli. Für k≈10 und N_base≈1500 → ~33k Modellaufrufe (machbar).  
   Hinweis: P95 ist kein Varianzfunktional → Approximation durch Indicator/Quantile-Delta (siehe Punkt 3 für präzisere Quantilmethode).  

2. Standardisierte Regressionskoeffizienten (SRC) + Partial Rank Correlation (PRCC)  
   Warum: Sehr effizient; liefert schnell Ranking für (nahezu) linear / monotonen Einfluss.  
   Nutzen: Quasi “Sanity Cross-Check” gegen Sobol; deckt lineare Dominenzen auf. PRCC robuster bei Nichtlinearitäten.  
   Aufwand: Gering – du nutzt bestehendes MC-Sample (Re-Use derselben 10k Ziehungen); nur Regressions-/Rangkorrelationen berechnen.  
   Zusatz: Liefert auch Vorzeicheninformation (Richtung des Effekts), was OAT pro Parameter schon zeigt, aber hier mit statistischer Signifikanz (Konfidenzintervall via Fisher-Z-Approx).

3. Quantil-Sensitivität (QSI) / “Quantile Importance” für P95 (und optional P99)  
   Warum: Varianzbasierte Maße ignorieren Tails; sicherheitsrelevant sind hohe Perzentile.  
   Ansatz:  
   a) Regressions-Quantile (z. B. lineares Modell oder Gradient Boosted Trees → Shapley auf P95-Vorhersage)  
   b) Oder: Conditioning – schätze ΔQ_p = Q_p(Y | X_i high) − Q_p(Y | X_i low) (mit High/Low als obere/untere 20%).  
   Nutzen: Zeigt, welche Parameter “Tail-Pusher” sind, auch wenn ihr Varianzbeitrag klein ist.  
   Aufwand: Gering bis moderat; nutzt vorhandenes Sample + binäres Conditioning.

4. Anteil an Schwellenüberschreitungen (Exceedance Sensitivity)  
   Metrik: ΔP(|Error| > T) pro Parameter ±Δ% Variation oder per High/Low Conditioning.  
   Warum: Direkt verknüpft mit SIL-Ziel (Spezifikationsverletzungsrate).  
   Nutzen: Direkter “Risk Lever” – welche Parametervariation reduziert Out-of-Spec Anteil am stärksten?  
   Aufwand: Niedrig (binäre Kennzeichnung + Differenzen).  
   Ergänzung: Auch als logit-Regressionsmodell (Feature Importance) darstellbar.

5. Gruppen-Sobol (Secure-Pfad Parametergruppe vs. Unsafe-Pfad Gruppe)  
   Warum: Architektur-Level Attribution: Wie viel Varianz kommt strukturell von “secure chain” vs. “unsafe chain”.  
   Nutzen: Rechtfertigt Investitionen (z. B. GNSS Quality Upgrade vs. Balise Timing).  
   Aufwand: Geringe Zusatzlogik: Du definierst Gruppen und aggregierst Parameter-Indices (SALib unterstützt Gruppierung).

## Staffel 2 – Vertiefung (Optional bei Bedarf)

6. Morris Screening (Elementary Effects)  
   Warum: Falls du demnächst die Parameterzahl deutlich erweiterst (>25).  
   Nutzen: Frühzeitiges Herausfiltern nicht relevanter Parameter vor teurer Sobol-Analyse.  
   Aufwand: Sehr niedrig (Trajectory-basiert). Nicht nötig solange Parameterraum schlank.

7. Borgonovo Delta (Moment-unabhängig)  
   Warum: Erkennt Einfluss auch wenn Parameter nur die Form der Verteilung (nicht Varianz) ändern.  
   Nutzen: Bei Mischverteilungen (Balise heavy tail) wertvoll.  
   Aufwand: Höher (Dichte-/CDF-Schätzungen). Eher später.

8. Shapley Effects (Verteilung auf Parameter-Koalitionen)  
   Warum: Voll faire Allokation inkl. Interaktionen (kooperative Spieltheorie).  
   Nutzen: Stakeholderfreundliche “Attribution” (Summe = 1).  
   Aufwand: Hoch (Sampling-Kombinatorik). Setzt stabile Hauptmodell-Laufzeit voraus.

9. Dynamische (zeitaufgelöste) Sobol-Kurven RMSE(t)  
   Warum: Zeitabhängige Dominanzverschiebungen (z. B. frühe Phase GNSS dominiert, später Odo/Drift).  
   Nutzen: Adaptive Kalibrierstrategien / Sensor Scheduling.  
   Aufwand: Hoch (multiplikative Last: Zeit × Parameter). Optimieren via Surrogate (Polynomial Chaos / GP) möglich.

10. Expected Shortfall (ES_p) Sensitivität (Tail-Schadensmaß)  
    Warum: P95 zeigt Schwelle, ES95 zeigt mittlere Schwere jenseits Schwelle.  
    Nutzen: Sicherheitsargumentation (Residual Risk).  
    Aufwand: Niedrig (Durchschnitt der Top (1-p)% Stichprobe). Sensitivitätsbewertung analog Quantile.

## Staffel 3 – Ergänzende Low-Cost Metriken

11. Elasticity / Log-Log Sensitivität: E_i = ∂log(Metrik)/∂log(θ_i) ≈ (ΔM/M)/(Δθ/θ)  
    Warum: Vergleichbarkeit auch bei unterschiedlich skalierten Parametergrößen.  
    Aufwand: Praktisch “kostenlos” – aus OAT ±Δ% Daten extrahierbar.

12. Contribution to Variance of Tail Indicator (Var[I(|Y|>T)])  
    Warum: Wenn Ausreißer-Risiko modelliert (binäre Hazard-Variable).  
    Aufwand: Re-Use Monte Carlo; ANOVA / logistic regression importance.

## Konkrete Vorschlagspipeline (Lean Erweiterung)

1. Sofort (nächster Sprint):
   - SRC + PRCC (RMSE_long, RMSE_2D, P95_long)
   - Quantil-Conditioning ΔQ95
   - Exceedance ΔP(|Error|>T) Ranking
2. Danach:
   - Sobol S_i & S_Ti (RMSE_long & RMSE_2D)
   - Gruppen-Sobol (Secure vs. Unsafe)
3. Optional Tail-Vertiefung:
   - ES95 Sensitivität
   - Quantil/ES Ergebnisse in Bericht als Tabelle (Rang konsistent / Divergenz markieren)

## Formeln & kurze Definitionen

- Sobol First Order: S_i = Var(E[Y|X_i]) / Var(Y)  
- Sobol Total: S_Ti = 1 − Var(E[Y|X_{−i}]) / Var(Y)  
- PRCC: ρ_partial( rank(X_i), rank(Y) | andere X_j )  
- ΔQ_p (Conditioning): Q_p(Y | X_i in High) − Q_p(Y | X_i in Low)  
- Exceedance Sensitivity: ΔP_T ≈ P(|Y|>T | X_i+Δ%) − P(|Y|>T | baseline)  
- Elasticity: E_i ≈ (M(θ_i(1+δ)) − M(θ_i(1−δ))) / (2 M_base δ)

## Warum diese Auswahl SIL1-relevant?

- Tail-orientierte Maße (Quantil, Exceedance, ES): direkt gekoppelt an Sicherheits-/Verfügbarkeitsanforderungen.
- Varianzzerlegung (Sobol): Nachvollziehbarkeit gegenüber Prüfern (transparente Modellbeherrschung).
- PRCC/SRC: Audit-fähige, einfache lineare/monotone Indikatoren (leicht zu dokumentieren).
- Gruppen-Sobol: Entscheidungsvorlage für Investitionen (z. B. lohnt bessere IMU?).

## Empfohlene Output-Struktur (Erweiterung results)

- `sensitivity_src.csv`
- `sensitivity_prcc.csv`
- `sensitivity_quantile_p95.csv`
- `sensitivity_exceedance_T{threshold}.csv`
- (später) `sensitivity_sobol_rmse_long.csv`, `..._rmse_2d.csv`, `..._p95_long.csv`
- (optional) `sensitivity_group_sobol.csv`

## Stichprobengrößen (Daumenregeln)

| Methode | Basis N (Parameter ~10) | Hinweis |
|---------|-------------------------|---------|
| SRC/PRCC | 5k–10k (Reuse) | CI via Bootstrap 500 |
| Quantil ΔQ95 | ≥ 5k | High/Low Bins ≥ 1000 Punkte |
| Exceedance ΔP | ≥ 10k falls Schwelle selten | Sonst Var hoch |
| Sobol | N_base 1500–2000 | Total Eval ≈ (2k+2)·N_base |
| Shapley | Surrogat-basiert | Erst nach Stabilisierung |

## Surrogate Option (falls Performance kritisch)
Für dynamische Sobol oder Shapley: Trainiere z. B. RandomForest/GBM → Ziehe Sensitivitäten via Permutation Importance + SHAP. Dokumentiere Modell-Fit (R², RMSE surrogate vs. true).

---

Wenn du möchtest, kann ich direkt die Implementations-Skelette für SRC/PRCC + Quantil/Exceedance in `sensitivity.py` ergänzen – sag einfach kurz Bescheid.

Möchtest du zuerst (a) schnelle Low-Cost Erweiterungen (SRC/PRCC/Quantil/Exceedance) oder (b) gleich Sobol integrieren?