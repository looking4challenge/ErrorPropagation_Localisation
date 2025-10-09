# Adaptive asymmetrische sichere Intervallbestimmung

Dieser Abschnitt dokumentiert das Design, die Annahmen und die Implementierungsdetails der adaptiven (potenziell asymmetrischen) sicheren Intervallgrenzen für die regelbasierte Fusion des Lokalisierungssystems.

## Ziel & Motivation

Das sichere Intervall [lower(t), upper(t)] kapselt zu jedem Zeitschritt t einen konservativen Bereich, in dem sich der wahre Positionsfehler des sicheren Pfades (Balise + Odometrie + Karte (+ ggf. weitere deterministische Komponenten)) mit hoher Wahrscheinlichkeit (≈ P99) befindet. Eine adaptive und potentiell asymmetrische Bestimmung reduziert künstliche Überkonservatismen der rein additiven, symmetrischen Summation und erlaubt geschwindigkeitsabhängige Fehlertopologien abzubilden (z. B. geschwindigkeitsproportionale Odometrie-Drift nur nach einer Richtung wirksam, Bias-Verschiebungen, kartengebundene systematische Offsets).

## Begriffe

* secure components: Fehlerkomponenten des sicheren Pfades (balise_error, odometry_residual, map_error, ...)
* unsafe path: Präzisionspfad (GNSS+IMU Surrogat)
* midpoint(t): 0.5*(lower(t)+upper(t)) (≠ 0 falls asymmetrisch)
* Mode: {midpoint, unsafe, unsafe_clamped}

## Datenbasis & Eingangssignale

Eingaben für die Intervallbestimmung je Aktualisierung:

1. secure Fehler-Samples (Aggregation über N Monte-Carlo Partikel oder Zeitfenster)
2. Geschwindigkeit v(t) für Speed-Binning
3. Konfigurationsparameter (Quantile, Bin-Breite, Mindest-Bin-Fraktion)

## Verfahren (Algorithmus)

1. Speed-Binning: Diskretisierung der momentanen Geschwindigkeiten in Bins der Breite Δv (Default 5 km/h; intern m/s konsistent) ⇒ Index b(i).
2. Bin-Stabilität: Ein Bin gilt als stabil, wenn n_bin ≥ min_bin_fraction * N_total. Instabile Bins nutzen globalen Fallback.
3. Quantilschätzung: Für stabilen Bin b: q_low(b) = Q_{p_low}(secure_b), q_high(b)=Q_{p_high}(secure_b). Standard p_low=1%, p_high=99%.
4. Monotonie-/Plausibilitäts-Check: Falls q_low(b) > q_high(b) (numerisches Artefakt) ⇒ Swap & Symmetrisierung.
5. Zuweisung: lower_i = q_low(b(i)), upper_i = q_high(b(i)). Instabile Bins: lower_i=-Q_{p_high}(global), upper_i=+Q_{p_high}(global).
6. Fallback-Eskalation: Wenn >20% der Bins instabil ⇒ globaler vollständiger Fallback (symmetrisch) zur Robustheit.
7. Midpoint & Asymmetrie: midpoint_i=0.5*(lower_i+upper_i). Aktuell sind viele Bins (noch) näherungsweise symmetrisch; Codepfad erlaubt jedoch verschobene Intervalle.
8. Update-Cadence: Wiederholung alle T_update Sekunden (Default 1 s). Dazwischen Nutzung letzter Bounds.

Pseudoformel:

Für Sample i mit Geschwindigkeit v_i:

  b_i = bin(v_i)
  (l_i, u_i) =
    (Q_{p_low}(S_b), Q_{p_high}(S_b)) falls stab(b)
    (-Q_{p_high}(S_all), +Q_{p_high}(S_all)) sonst
  Falls Anteil instabiler Bins > θ_fallback ⇒ (l_i, u_i)=(-Q_{p_high}(S_all), +Q_{p_high}(S_all))

## Parameter & Defaults

| Parameter | Bedeutung | Default | Einfluss |
|-----------|-----------|---------|----------|
| quantile_low_pct | Unteres Sicherheitsquantil | 1.0 | Steuert Untergrenze; kleinere Werte ⇒ breiter |
| quantile_high_pct| Oberes Sicherheitsquantil | 99.0 | Tail-Abdeckung; höhere Werte ⇒ breiter |
| speed_bin_width  | Geschwindigkeitsbinbreite (m/s) | 5 km/h (≈1.389 m/s) | Feinheit Geschwindigkeitsabhängigkeit |
| min_bin_fraction | Mindestanteil eines Bins | 0.05 | Robustheit gegen spärliche Bins |
| update_cadence_s | Aktualisierungsintervall | 1.0 | Reaktionsgeschwindigkeit vs. Varianz |
| fallback_threshold_fraction | Anteil instabiler Bins für globale Eskalation | 0.20 | Stabilitäts/Güte-Kompromiss |
| blend_steps | Anzahl Schritte lineare Modus-Glättung | 5 | Übergangsglättung, reduziert Sprünge |

## Sicherheitsgarantie

Durch Clamping (np.clip(fused, lower, upper)) wird garantiert:

  lower_i ≤ fused_i ≤ upper_i  ∀ i.

Damit ist das asymmetrische Sicherheitsintervall eine harte Schranke für den ausgegebenen Fusionspfad. Konservativität (True Positive Rate) wird über Wahl hoher p_high und robuste Fallbacks gewährleistet. Fehlende formale Unabhängigkeitsbeweise werden durch empirische Abdeckungstests (geplant) ergänzt.

## Qualitätsheuristik (Entscheidung B)

Nutzung des unsafe Pfades nur wenn (available ∧ lower_i ≤ unsafe_i ≤ upper_i). Dies minimiert unnötiges Clamping und erhält Präzision innerhalb Sicherheitsgrenzen.

## Glättung (Entscheidung C)

Lineare Blendung über blend_steps zwischen altem und neuem Modusziel reduziert derivative Jumps. Exponentielle Variante (alpha-Smoothing) verworfen (derzeit optional) wegen potenziell langsamer Konvergenz bei abrupten Outagen.

## Adaptive Aktualisierung (Entscheidung D)

Update alle update_cadence_s Sekunden begrenzt Rechenaufwand (O(N_bins)) und reduziert Quantilrauschen. Zwischenzeitlich werden Bounds zwischengespeichert (stateful).

## Asymmetrie-Perspektive (zukünftig)

Auslöser für echte Asymmetrie könnten sein:

1. Richtungsabhängige Kartendrift (systematische Offsets)
2. Vorzeichenbehaftete Odometrie-Skalierungsfehler über längere Strecken
3. Bias-Korrektur im Präzisionspfad nur in einer Richtung wirksam
4. Anfahr-/Bremsphasen mit nicht-symmetrischen Beschleunigungsfehlern

Sobald empirisch belegt, können q_low und q_high entkoppelt parametriert werden (z. B. unterschiedliche Prozentile p_low!=100-p_high).

## Limitierungen

* Nutzung von einfachen Per-Bin Quantilen ⇒ kein explizites Modellieren von Korrelationen innerhalb Bins (ggf. konservativ).
* Empirische Quantile bei kleinen Bins volatil → globaler Fallback verwässert Geschwindigkeitsabhängigkeit.
* Kein direktes Joint-Modell longitudinal/lateral; Querintervall gegenwärtig symmetrisch.
* Keine formale SIL1 Nachweisführung hier enthalten; dieser Abschnitt liefert design rationale & nachvollziehbare Heuristiken.

## Validierungs- & Monitoring-Ansätze

1. Coverage-Test: Prüfe Anteil(|secure_error_i| ≤ upper_i & ≥ lower_i) ≥ Ziel (z. B. 98.5% für nominelles P99 mit Sicherheitsmarge).
2. Drift-Monitoring: Warnung falls Anteil unsafe_clamped > Schwelle (z. B. 10%).
3. Quantil-Stabilität: Rolling Vergleich der adaptiven Bounds vs. global P99; Δ ≤ definierte Toleranz.
4. Regressionstest: Snapshot quantile bias Änderung <5 %-Pkt nach Parametervariationen.

## Referenz auf Code

* Funktion `compute_secure_interval_bounds` in `src/fusion.py` (Adaptive Binning & Fallback)
* Funktion `rule_based_fusion_step` (Moduswahl & Clamping)
* CLI Flags: `--interval-update-cadence-s`, `--no-adaptive-interval`, `--fusion-stats`, `--export-interval-bounds`

## Offene Punkte

* Exponentielle Glättungsoption evaluieren (Stabilität vs. Reaktionszeit)
* Export vollständiger Zeitreihe der Bounds für Audit (Option `secure_interval_bounds_timeseries.csv`)
* Erweiterung auf lateral asymmetrisch bei Datenbasis

## Kurzzusammenfassung

Das adaptive Verfahren reduziert konservative Überschätzung gegenüber rein additiver Summation, behält aber Sicherheitsgarantie via Clamping & Fallback bei. Designentscheidungen A–D sind implementiert und dokumentiert; zukünftige Arbeit fokussiert auf echte Asymmetrie-Ausnutzung und Coverage-Monitoring.
