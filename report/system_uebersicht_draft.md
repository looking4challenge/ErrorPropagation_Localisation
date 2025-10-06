# Systemübersicht & Annahmen (Draft zur Review)

Status: Phase 1 (Workspace-Scan abgeschlossen – Nutzer-Review ausstehend)
Erstellt: 2025-10-06

## 1. Betriebsprofil

- Geschwindigkeitsbereich: 0–60 km/h (lokaler Rangier-/Kurzstreckenbetrieb; keine Hochgeschwindigkeit → Latenz × v Effekte begrenzt)
- Beschleunigungsprofil: moderat (|a| ≤ 0.7 m/s²) → begrenzte dynamische IMU-Anforderungen; lineare Modelle ausreichend
- Streckenmodusanteile: open 70%, urban 25%, tunnel 5% (Tunnelanteil klein → GNSS-Ausfälle selten aber sicherheitskritisch für Validierung)

## 2. Subsystemarchitektur (hybride Lokalisierung)

Sicherer Pfad (Safety-Relevanz, SIL1 Kontext):

- Balisen (BRV4) Ereignis-getriggert (nicht 1 Hz limitiert)
- Zwei-Achsen Odometrie (nicht angetriebene, nicht gebremste Achse → Schlupfarm / schlupfkompensiert per Architektur)
- Digitale Karte (präzise Track & Referenzpunkte)

Nicht-sicherer Pfad / Erweiterter Präzisionspfad:

- GNSS (+ optional RTK / PPP Modi; Parameter noch zu spezifizieren)
- IMU (SIL1-Hardware optional für zukünftige Schlupfkompensation; aktuell nur im nicht-sicheren Pfad genutzt)
- Fusions-Proxy: ekf_simple (bestätigt)

Fehlerkopplung: Kartenfehler wirken korreliert auf beide Pfade → systematische Offsets nicht vollständig wegfusionierbar.

## 3. Zielmetrik & Anforderungen

- Primäre Anforderung (Nutzer): Längs-RMSE < 0.20 m (gesamtes hybrides System im nominalen Betrieb)
- Zusätzliche Berichtskennzahlen: μ, σ, RMSE, P50, P90, P95, P99 (Longitudinal / Lateral / 2D), Bootstrap-CIs
- Verfügbarkeit / Ausfallmechanismen (GNSS, Balise) werden später erweitert (GNSS Daten fehlen noch)

## 4. Validierte Fehlerquellen aus bestehenden Analysen

### 4.1 Balisen / BRV4

Zwei Modellzustände vorhanden:

1. Legacy (Schema 1.x – getrimmte Signalqualität λ=0.05, Cap 10 cm):
   - Längs: μ ≈ 13.6 cm, σ ≈ 1.6 cm, P95 ≈ 15.8 cm, P99 ≈ 20.7 cm
   - Quer: μ ≈ 3.7 cm, σ ≈ 0.7 cm, P95 ≈ 5.1 cm, P99 ≈ 6.1 cm
   - Varianzanteile längs: Signalqualität 55%, Latenz 40%, EM 2.5%, Antenne 2.2%
2. Schema 2.0 (Heavy Tail Exponential λ=0.2 ungetrimmt):
   - Längs: μ ≈ 5.10 m (Heavy Tail dominiert) – konservativ, vermutlich unrealistisch ohne empirisches Tail-Bounding
   - Ausfallraten: linear ≈2.9% (30 km/h) oder Markov p_fail_given_ok=0.01 / p_stay_failed=0.9 → ~9.1% steady-state

Draft-Entscheidung für initiale Systemsimulation: Start mit Legacy-Modell (realitätsnäher für Perzentile) + optionaler Heavy-Tail Szenario-Flag für konservative Stressfälle. (Bestätigung erforderlich)

### 4.2 Odometrie (schlupfkompensiert durch Achswahl)

- RMS Positionsfehler Zwischen-Balisen (Kontext-Modell): 4.47 mm
- 99%-Perzentil: 12.74 mm
- Dominanz: Quantisierung (≈65% Varianz, ±13.4 mm Schrittbreite bei 100 pulses/rev)
- Drift (Dead-Reckoning): ≈10 mm/km
- Schlupfmodell: vorerst weggelassen (Architektur reduziert Schlupf) – zukünftige Erweiterung offen für IMU-gestützte Erkennung

### 4.3 Digitale Karte

- Geometrie σ (1σ): Längs ≈1.9 cm, Quer ≈1.4 cm
- Skalierungsfehler: 0.006% Distanz (wirksam >5 km relevant)
- Korrelationsmatrix (Hauptfehlerquellen exemplarisch): Karte korreliert stark mit GNSS (0.8) und Balise (0.65) → systemische Offsets

### 4.4 Noch nicht spezifizierte Komponenten

- GNSS: Werte für Bias, stochastisches Rauschen (open/urban/tunnel), Ausfallwahrscheinlichkeiten fehlen (offene Frage)
- IMU: Bias- und Noise-Dichten nicht in vorhandenen Dokumenten (werden durch Standard Low-/Mid-Grade Vorschläge ersetzt, pending)
- Zeitstempel/Jitter: Balise Latenz konservativ 10 ms ± 2 ms + ±1 ms Uniform; Fusion-Latenz / Jitter Proxy noch festzulegen (Platzhalter 100 ms / 20 ms in model.yml)

## 5. Geplante Modellierung & Fehlerpropagation

| Fehlerquelle | Modellierung (initial) | Parameterquelle | Relevanz Longitudinal | Relevanz Lateral | Bemerkung |
|--------------|------------------------|-----------------|-----------------------|------------------|-----------|
| Balise Messfehler | Legacy truncated exponential composite | balise_error_analysis.md | HOCH | MITTEL | Heavy-Tail Alternative optional |
| Odometrie Quantisierung | Deterministic ±Δ/2 uniform | odometrie_error_analysis.md | MITTEL | NIEDRIG | Dominiert bei langen Intervallen |
| Odometrie Drift | Lineares Drift+Rauschen | odometrie_error_analysis.md | MITTEL | NIEDRIG | ~10 mm/km |
| Karten Geometrie | Normal + exp Interpolation | map_error_analysis.md | MITTEL | MITTEL | Korrelierter Offset |
| Karten Skalierung | Proportionaler Fehler | map_error_analysis.md | NIEDRIG (<5 km) | NIEDRIG | Distanzabhängig |
| GNSS Bias/Noise | Normal / lognormal (TBD) | (offen) | HOCH | HOCH | Open vs urban vs tunnel |
| GNSS Ausfälle | Bernoulli pro Zeitschritt | (offen) | HOCH | HOCH | Tunnel ↑ |
| IMU Bias/Drift | Random Walk + Bias | (Standardvorschlag) | MITTEL | MITTEL | Für Dead-Reckoning bei GNSS-Ausfall |
| Balise Ausfall | Linear oder Markov | balise_error_analysis.md | MITTEL | MITTEL | Wahl pending |
| Zeit-Latenz Fusion | Stoch. Delay → Position = v·Δt | balise_error_analysis.md | MITTEL | NIEDRIG | v ≤ 60 km/h begrenzt |

Nicht berücksichtigt (initial): Extreme Wetter (Regen/Laub/Schnee) → keine quantifizierten Daten; Oberleitungsreflexionen GNSS (multipath) → später falls Daten; Weichen-Topologiefehler → binär, separat qualitativ.

## 6. Korrelationen (Draft)

Basierend auf map_error_analysis und Systemlogik (noch zu bestätigen):

- Karte ↔ GNSS: ρ ≈ 0.8 (systematischer Projektionseinfluss)
- Karte ↔ Balise: ρ ≈ 0.65 (gemeinsame Referenzierung)
- Balise ↔ Odometrie: ρ ≈ 0.85 (Balisen-Kalibrierung Odo)
- Odometrie ↔ GNSS: ρ ≈ 0.25 (geschwindigkeits-/trajektorienabhängige Korrelation)
- GNSS ↔ Balise: ρ ≈ 0.30 (gemeinsame Nutzung Kartenanker)
(Detail: Diese Matrix wird dimensioniert auf konkrete Parametervektoren; offene Feinabstimmung)

## 7. Sensitivitätsansatz

- OAT ±10% auf skalare Nennwerte (Varianz & Perzentil-Änderung ΔRMSE und ΔP95)
- Ranking via relativer Änderung in Longitudinal RMSE
- Sobol (First/Total) deferred bis Parameter-Freeze (N_samples hoch → Rechenkosten)

## 8. Reproduzierbarkeit

- Seeds: globaler random_seed (12345 vorläufig) + dokumentierte Config-Hash
- Bootstrap: B=500 (kann bei N=10000 ausreichend) – Performance vs. Stabilität balanciert
- Output: Ergebnisse als CSV (metriken.csv), sensitivitaet.csv, Plots in figures/

## 9. Offene Punkte (User-Bestätigung benötigt)

1. Balise-Modellwahl initial: Nur Legacy oder Dual (Legacy + Heavy Tail Szenario)?
2. GNSS Parameter-Sets (open/urban/tunnel): Bitte angeben oder „Standardvorschlag liefern“.
3. IMU Standard (accel_bias ~0.01 m/s², gyro_bias ~0.05 °/s, noise_density ~0.1) akzeptabel? Anpassung?
4. Balise Ausfallmodell: linear vs Markov für Start?
5. Fusion-Latenz/Jitter Platzhalter (100 ms / 20 ms): realistisch für Ihren Stack? Sonst Werte nennen.
6. Korrelationen Draft übernehmen oder Anpassungen?

## 10. Nächste Schritte nach Review

- Einarbeiten Feedback → finalize config/model.yml
- decisions.log ergänzen
- Phase 2: Korrelationsvalidierung + Testplanung

Bitte Feedback / Korrekturen je Abschnitt (Nummer + Änderung). Falls „ok“, vermerken.
