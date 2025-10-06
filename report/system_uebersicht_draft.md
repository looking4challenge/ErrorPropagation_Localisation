# Systemübersicht & Annahmen (Draft zur Review)

Status: Phase 1 (Workspace-Scan abgeschlossen – konsolidiert mit `systemdescription/spezifikationen.md` – Nutzer-Review ausstehend)
Erstellt: 2025-10-06 (aktualisiert mit Spezifikationsabgleich)

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

### 4.1 Balisen / BRV4 (konsolidiert)

Quellen: `spezifikationen.md` (Abschnitte 3 / 3.3 Tabelle) & interne Monte-Carlo-Auswertung.

Konfligierende Angaben & Konsolidierung:

| Aspekt | Spezifikationen | Vorheriger Draft | Entscheidung (Simulation v0) | Begründung |
|--------|-----------------|------------------|------------------------------|------------|
| Mittlerer Längsfehler (nominal) | 10.2 cm @ 30 km/h (alternativ 12.4 cm „sicher") | 13.6 cm (aggregierte Legacy) | 12.0 cm | Mittelwert zwischen empirischem 10.2 und konservativem 13.6 zur robusteren Abdeckung; spiegelt Geschwindigkeitsmix (30–60 km/h) wider |
| σ Längs | 2.8–3.1 cm (68% Band) | 1.6 cm | 2.2 cm | Reduziert gegenüber 2.8 (Filter & Kalibrierung), höher als 1.6 (frühere Untermodellierung) |
| P95 Längs | 19.8 cm | 15.8 cm | 18.0 cm | Interpolation aus neuem σ und moderatem Tail |
| P99 Längs | 19.8 cm (gleiche Zahl im Text – indiziert Sättigung) | 20.7 cm | 22.0 cm | Leicht angehoben zur Tail-Absicherung |
| Mittlerer Querfehler | 2.9 cm | 3.7 cm | 3.2 cm | Mittelweg; Montage-/Karteneffekte kombiniert |
| σ Quer | 1.1–1.2 cm | 0.7 cm | 0.9 cm | Korrigiert für zusätzliche EM & Ausrichtung |
| P95 Quer | 6.1 cm | 5.1 cm | 5.8 cm | Konsistenz mit σ 0.9 + leichter Tail |
| Ausfall P_fail(v) | 0.02 + 0.0003·v (v km/h) | 2.9% bei 30 km/h (linear) | Funktion übernommen | Funktion direkt aus Spezifikation |
| Latenz t_latenz | 6–14 ms (μ=10, σ=2) | 10 ms ±2 ms + ±1 ms Uniform | N(10ms,2ms) trunc [6,14] ms | Vereinfachung (Uniform-Anteil vernachlässigt) |
| Antennenoffset | σ=2 cm (längs/quer) | — | N(0,0.02) m | Direkt aus Spezifikation |
| EM Störung | Rayleigh σ=1.2 cm | Varianz 2.5% Anteil (implizit) | Rayleigh(σ=0.012 m) | Parametrisch für additive Komponente |
| Multipath | Exp λ=0.05, cap 5 cm | Truncated Exp cap 10 cm | Truncated Exp λ=0.05 cap 8 cm | Kompromiss zwischen beiden Caps |
| Witterung | Uniform ±1.5 cm | Nicht modelliert | U(-0.015,0.015) m | Geringer Beitrag, aber stoch. Breite |

Generatives Modell (Längs):

ε_längs = v·t_latenz  + N(0,0.02)  + E_trunc(λ=0.05, cap=0.08)·w_tail  + R_rayleigh(σ=0.012)  + U(-0.015,0.015)

mit w_tail=0.15 Mischanteil (Kalibrierung gegen Ziel-P95/P99). Quer analog ohne Latenzterm.

Begründung Konfliktlösung: Frühere 13.6 cm beinhaltete stärkere Tail-Gewichtung bei höherer Referenzgeschwindigkeit; Spezifikationswert 10.2 cm erscheint für 30 km/h, aber Zielsystem arbeitet bis 60 km/h. Mittelwert 12 cm minimiert Risiko Unterabschätzung der RMSE. Tail-Anhebung nötig zur konservativen SIL1-Betrachtung.

Heavy-Tail Szenario (separater Stress-Test): Setze w_tail=0.35 und cap=0.12 m → erwartetes P99 ~0.28–0.30 m.

Balisen-Ausfallmodell (aktualisiert nach Review): Ziel mittlere Nicht-Detektion 1 / 10000 Balisen (p_miss≈1e-4). Aktiviertes Markov-Modell für potenzielle Clustering-Erkennung:

Zwei-State Kette (OK, DEGRADED) für „technische Degradation" (optional) und Ereignis-spezifischer Detektionsversuch:

1. Zustandsübergänge pro Balisen-Ereignis: p(OK→DEG)=1e-6, p(DEG→OK)=0.01 ⇒ steady-state P(DEG)≈1e-4.
2. Detektionswahrscheinlichkeit je Ereignis:
   - OK-Zustand: p_detect=0.99995 (isolierte sporadische Ausfälle p_iso=5e-5)
   - DEG-Zustand: p_detect=0.95 (unterliegende Störung)

Erwartete gesamt P_miss ≈ 1e-4 (OK Anteil · p_iso + DEG Anteil · (1 − 0.95)).
Für Basis-Simulation kann optional die DEG-Zustandsebene deaktiviert werden (reduziert auf Bernoulli p_miss=1e-4). Parameter wandern in `model.yml` (section sensors.balise.failure_model).

### 4.2 Odometrie (schlupfkompensiert durch Achswahl)

Referenzen: `spezifikationen.md` (Odometrie-Abschnitte), `odometrie_error_analysis.md`.

Mess- & Modellparameter:

| Kenngröße | Wert / Modell | Quelle / Kommentar |
|-----------|---------------|--------------------|
| Quantisierungsschritt | 13.4 mm (100 pulses/rev, Radumfang ~1.34 m Beispiel) | Abgeleitet; dom. Varianzanteil ~65% |
| RMS Zwischen-Balisen | 4.47 mm | Voranalyse bestätigt |
| 99%-Perzentil | 12.74 mm | Voranalyse |
| Systematische Drift | 10 mm/km (vor Kalibrierung) | Voranalyse |
| Radverschleiß Spannweite | -8.97% Umfang (Rad-Durchmesser 850→780 mm) | Spezifikation (definierter Bereich bestätigt) |
| Adaptive Kalibrierung | Umfangskorrektur pro Balisensegment | Spezifikation |
| Schwelle Umfangsanpassung | 1 mm über 100 Messzyklen | Spezifikation |
| Residual Umfangsfehler (typisch) | ≤0.10 m pro Segment (theoretisch max 0.39 m) | Spezifikation, konservativ: 25% der Obergrenze |

Simulation Implementation v0:

1. Stochastischer inkrementeller Fehler = Quantisierung (Uniform(-Δ/2, Δ/2)).
2. Driftanteil = Normal(0, (0.010 m / km)·Δd) pro Segment mit Re-Nullstellung an Balise.
3. Residual systematischer Umfangsfehler: Uniform(-0.03, 0.03) m pro Segment (aktualisierte Info). Optional Stress: Uniform(-0.10,0.10) m.

Erläuterung Residual Umfangsfehler (aktualisiert 3 cm / 10 cm Extrem): Dieser Term modelliert den verbleibenden systematischen Distanzoffset zwischen zwei Balisen nach Anwendung der adaptiven Umfangskorrektur. Er bündelt:

- Verzögerte Erkennung sehr kleiner Umfangsänderungen (<1 mm Schwelle)
- Temperatur-/Druck-induzierte elastische Radumfangsvariation
- Nichtmodellierte minimale Schlupfanteile auch bei nicht-angetriebener Achse

Die typische Spanne jetzt ±0.03 m (3 cm) (≈0.003% eines 1 km Segments) basiert auf neuer Betriebs-/Kalibrier-Rückmeldung. Ein Extrem-/Stressfall wird mit ±0.10 m (10 cm) modelliert, um seltene Kombinationen aus Temperaturgradient, verzögerter Kalibrierung und geringer Balisen-Dichte abzudecken.

Schlupfmodell bleibt deaktiviert (Annahme: nicht angetriebene Achse → minimiert Schlupf). Erweiterung: Koppelung an IMU longitudinal acceleration threshold (Phase ≥4, falls benötigt).

### 4.3 Digitale Karte (konsolidiert)

Primärkomponenten gem. Spezifikation (§2.4 / Parametertabelle):

| Komponente | Modell | Parameter | Bemerkung |
|------------|--------|-----------|-----------|
| Gleisachse Vermessung | Normal | σ=0.020 m | Baseline geometrisch |
| Höhenmodell (quer Proxy) | Normal | σ=0.015 m | Fließt in quer zusammen |
| Interpolation | Exponential | λ=0.02 (mean 0.02 m) | Längs additiv (kleiner Beitrag) |
| Proportionale Skalierung | Kombiniert (N + U + N) | σ_eff ≈ 0.00006 * d | Aus 0.01%, ±0.005%, 0.003% (RMS) |
| Korrelation Länge | Exponential Cov(r) | r₀=75 m | Räumlich korreliert |

Aggregiertes Simpelformat v0 (für MC-Leistung):
Längsfehler Karte ~ Normal(0, 0.019 m) + Exp(λ=0.02) getrimmt 5 cm (gewicht 0.3). Quer ~ Normal(0, 0.014 m). Proportionaler Skalierungsfehler α ~ Normal(0,6e-4) (entspricht 0.06%) angewendet auf Distanz > 2 km; darunter vernachlässigbar.

Systematische Offsets (gemeinsame Referenz) erzeugen Korrelation mit Balise & GNSS (s.u.).

### 4.4 GNSS / IMU / Fusion (nach Review bestätigt)

GNSS (Defaults akzeptiert):

| Umgebung | Bias (N(0,σ_b)) | Messrauschen 1σ | Outage p/epoch | Tail Zusatz (Multipath) |
|----------|-----------------|-----------------|---------------|------------------------|
| Open | 0.25 m | 0.30 m | 0.01 | – |
| Urban | 0.50 m | 0.80 m | 0.05 | Exp(λ=2, cap 3 m, w=0.1) |
| Tunnel | n/a (kein Fix) | n/a | 1.0 | – |

IMU (Automotive / moderne Sensorplattform, angelehnt an aktuelle lidar-gestützte Systemintegrationen):

| Parameter | Modell | Wert |
|-----------|--------|------|
| accel_bias | N(0,σ) | σ=0.005 m/s² |
| gyro_bias | N(0,σ) | σ=0.02 °/s |
| accel_noise_density | Weißrauschen | 0.05 m/s²/√Hz |
| gyro_noise_density | Weißrauschen | 0.01 °/s/√Hz |
| Bias Random Walk Zeitkonstante | Exponential | τ=900 s |

Fusion-Latenz (angepasst): Δt_fusion ~ N(20 ms, 5 ms) trunc [10,35] ms; Jitter wird in dieser Verteilung absorbiert. Effektiver Positionsfehler-Term in Proxy-Fusion: v · Δt_fusion · (1 − K_gain) mit initialem linearen Gain K_gain≈0.6 (reduziert Einfluss auf finale Schätzung).

Hinweis: GNSS Parameter jetzt als ACCEPTED markiert (nicht mehr „unsicher“). IMU Parameter aktualisiert (niedrigere Bias-/Noise-Werte vs. v0 Proxy). Latenz drastisch reduziert – erwartete Verringerung des Latenz-bedingten Beitrags zur Längsvarianz.

## 5. Funktionale Verarbeitungspfade & vereinfachte Fehlermodelle (Stakeholder-Summary)

Ziel dieses Abschnitts: Technisch verständliche Übersicht ohne vertiefte Statistik. Jeder Pfad liefert Positionsinformation; Fehlerquellen addieren sich (vereinfachte additive Modellierung) oder wirken multiplikativ bei Skalenfehlern.

### 5.1 Balisen-Verarbeitungspfad

1. Detektion (Antenne + Signalprozess): Rohsignal → Telegramm → Zeitstempel.
2. Zeitstempel-Korrektur (Verarbeitungs- / Kommunikationslatenz).
3. Zuordnung zur Karten-Referenzposition (Balise-ID → Karte).
4. Ausgabe eines absoluten Positionsankers.

Vereinfachtes Fehlermodell (Längsrichtung):

Positionsfehler_balise_längs ≈ (Geschwindigkeit · Latenz) + Antennenoffset + Signalqualität/Tail + EM-Störungen + Witterung + Kartenoffset

Typische Beiträge (Richtwerte):

- Latenzterm: v( m/s ) · 0.010 s (σ 0.002 s) → bei 10 m/s ≈ 0.10 m ±0.02 m
- Antennenoffset: Normal(0, 0.02 m)
- Tail (Ausreißer): mit 15% Wahrscheinlichkeit zusätzliche Exponential-Komponente (λ=0.05, auf 0.08 m begrenzt)
- EM-Störung: Rayleigh(σ=0.012 m) ≈ mittlerer Beitrag ~0.015 m
- Witterung: Uniform(-0.015, 0.015) m
- Kartenoffset: Normal(0, 0.019 m)

Interpretation: Dominanter Anteil ist bei höheren Geschwindigkeiten der Latenzterm; darunter systematische Offsets (Karte, Antenne) und stochastische Streuung (EM, Tail).

### 5.2 Odometrie-Verarbeitungspfad

1. Inkrementzählung (Impulsgeber / Encoder) → Weginkrement.
2. Quantisierung (Schrittweite ≈ 13.4 mm Beispiel).
3. Drift & Umfangsanpassung (Radverschleiß, adaptive Kalibrierung per Balisenabstand).
4. Integration bis zum nächsten Balisen-Anker → relative Position.

Vereinfachtes Fehlermodell Segment (zwischen Balisen):

Positionsfehler_odo_segment ≈ Quantisierungsrauschen + Drift + Residual Umfangsfehler (±0.01 m) + (optional Stress: zusätzlicher systematischer Block)

Typische Beiträge (für 1 km Segment):

- Quantisierung (RMS ~4–5 mm)
- Drift (10 mm/km vor Korrektur, abgeschnitten durch Balise-Reset)
- Residual Umfang (3 cm Band)

Interpretation: Die Odometrie ist sehr präzise kurzfristig; Fehler wachsen zwischen Balisen kontrolliert und werden bei jedem Balisen-Event zurückgesetzt.

### 5.3 Digitale Karte Verarbeitungspfad

1. Abfrage der Referenzgeometrie (Gleisachse + Referenzpunkte).
2. Interpolation zwischen Stützpunkten.
3. Projektion externer Sensoren (Balise, GNSS) auf Gleisreferenz.

Vereinfachtes Fehlermodell:

Positionsfehler_karte_längs ≈ Geometriefehler + Interpolationsfehler + Skalierungsfehler(d)  
Positionsfehler_karte_quer ≈ Geometriefehler_quer + Höhenmodellfehler

Typische Beiträge:

- Geometrie: Normal(0, 0.019 m) längs / Normal(0, 0.014 m) quer
- Interpolation (Exp(λ=0.02), getrimmt 0.05 m) kleiner Zusatz (~0.02 m Mittelwert, Gewicht 0.3)
- Skalierung: α·d mit α ~ 0.0006 (0.06%) nur spürbar bei langen Strecken >2 km

Interpretation: Kartenfehler sind relativ klein, aber systematisch und damit korreliert zwischen Balise, GNSS und Odometrie (über Korrekturen). Sie setzen den „gemeinsamen Boden“ der Genauigkeit.

### 5.4 Zusammenspiel der Pfade

- Balise liefert absolute Anker mit moderater Einzel-Unsicherheit (dominiert durch Latenz + Offsets); reduziert Odometrie Drifts.
- Odometrie füllt die Zeit/Gleisdistanz zwischen Balisen hochauflösend mit geringer Fehlerzunahme.
- Karte projiziert/fusioniert beide Pfade und definiert systematische Offsets (→ Korrelationen).

Ein vereinfachtes longitudinales Gesamtmodell (Qualitativ):

Positionsfehler_total ≈ Gewicht(Balise)·Positionsfehler_balise  + Gewicht(Odo)·Positionsfehler_odo  + Kartenoffset  (+ GNSS/IMU Beiträge im erweiterten Pfad)

Gewichtungen werden später im Fusions-Proxy (ekf_simple) parametriert (Heuristik: Varianz-invers als Start).

### 5.5 Warum additive Modelle hier ausreichend (für Stakeholder)

Obwohl einige Fehlerquellen nicht strikt additiv sind (z.B. Kopplungen, nichtlineare Filter), liefert die additive Näherung konservative Schätzungen für Streuung und Perzentile bei homogenen Betriebsbedingungen (<60 km/h) und moderaten Latenzen. Detailliertere Kopplung (z.B. Kovarianzmatrix, Copula) wird intern in der Monte-Carlo Pipeline berücksichtigt, ist für das grundsätzliche Verständnis aber nicht erforderlich.

---

## 6. Geplante Modellierung & Fehlerpropagation

| Fehlerquelle | Modellierung (initial) | Parameterquelle | Relevanz Longitudinal | Relevanz Lateral | Bemerkung |
|--------------|------------------------|-----------------|-----------------------|------------------|-----------|
| Balise Messfehler | Legacy truncated exponential composite | balise_error_analysis.md | HOCH | MITTEL | Heavy-Tail Alternative optional |
| Odometrie Quantisierung | Deterministic ±Δ/2 uniform | odometrie_error_analysis.md | MITTEL | NIEDRIG | Dominiert bei langen Intervallen |
| Odometrie Drift | Lineares Drift+Rauschen | odometrie_error_analysis.md | MITTEL | NIEDRIG | ~10 mm/km |
| Karten Geometrie | Normal + exp Interpolation (konsolidiert) | spezifikationen.md & map_error_analysis.md | MITTEL | MITTEL | Korrelierter Offset |
| Karten Skalierung | Proportionaler Fehler (α ~ N(0,6e-4)) | spezifikationen.md | NIEDRIG (<2 km) | NIEDRIG | Ab >2 km relevant |
| GNSS Bias/Noise | Normal / lognormal (TBD) | (offen) | HOCH | HOCH | Open vs urban vs tunnel |
| GNSS Ausfälle | Bernoulli pro Zeitschritt | (offen) | HOCH | HOCH | Tunnel ↑ |
| IMU Bias/Drift | Random Walk + Bias | (Standardvorschlag) | MITTEL | MITTEL | Für Dead-Reckoning bei GNSS-Ausfall |
| Balise Ausfall | Linear oder Markov | balise_error_analysis.md | MITTEL | MITTEL | Wahl pending |
| Zeit-Latenz Fusion | Stoch. Delay → Position = v·Δt | balise_error_analysis.md | MITTEL | NIEDRIG | v ≤ 60 km/h begrenzt |

Nicht berücksichtigt (initial): Extreme Wetter (Regen/Laub/Schnee) → keine quantifizierten Daten; Oberleitungsreflexionen GNSS (multipath) → später falls Daten; Weichen-Topologiefehler → binär, separat qualitativ.

## 7. Korrelationen (Draft)

Aktualisierte arbeitsfähige Korrelationsannahmen (werden in Phase 2 validiert):

| Paar | ρ Annahme | Begründung |
|------|-----------|------------|
| Karte–GNSS | 0.80 | Gemeinsame Projektion & Map-Matching |
| Karte–Balise | 0.65 | Referenzübernahme bei Event |
| Balise–Odometrie | 0.80 (vorher 0.85) | Odometrie-Neuinitialisierung dämpft Varianz leicht |
| Odometrie–GNSS | 0.25 | Geschwindigkeits-/Trajektorienkopplung gering |
| GNSS–Balise | 0.30 | Gemeinsame Kartenoffsets |
| IMU–Odometrie | 0.40 | Gemeinsame Dynamik (Beschleunigung → Geschwindigkeit) |
| IMU–GNSS | 0.20 | Gemeinsame Bewegungsdynamik, unterschiedliche Fehlerarten |

Toleranz für Validierung: |ρ_sample − ρ_target| ≤ 0.05 (Konfig `rho_tol`).

## 8. Sensitivitätsansatz

- OAT ±10% auf skalare Nennwerte (Varianz & Perzentil-Änderung ΔRMSE und ΔP95)
- Ranking via relativer Änderung in Longitudinal RMSE
- Sobol (First/Total) deferred bis Parameter-Freeze (N_samples hoch → Rechenkosten)

## 9. Reproduzierbarkeit

- Seeds: globaler random_seed (12345 vorläufig) + dokumentierte Config-Hash
- Bootstrap: B=500 (kann bei N=10000 ausreichend) – Performance vs. Stabilität balanciert
- Output: Ergebnisse als CSV (metriken.csv), sensitivitaet.csv, Plots in figures/

## 10. Offene Punkte / Status

| Punkt | Thema | Status | Aktion nötig |
|-------|-------|--------|--------------|
| 1 | Balise Konsolidierung & Heavy-Tail Flag | BESTÄTIGT (mit p_miss Korrektur) | optional Tail-Stress aktivieren später |
| 2 | GNSS Defaults | BESTÄTIGT | keine |
| 3 | IMU Parameter | AKTUALISIERT (automotive) | keine |
| 4 | Balise Ausfallmodell | MARKOV AKTIV | Feinjustierung nach erster Sim falls Abweichung P_miss |
| 5 | Fusion Latenz | REDUZIERT 20±5 ms | Validierung Einfluss nach Sim |
| 6 | Korrelationen | BESTÄTIGT | Phase 2 Validierung |
| 7 | Residual Umfangsfehler | AKTUALISIERT (±0.03 m, Stress ±0.10 m) | Nach MC-Befund ggf. Verengung |

Offen zur Entscheidung nach ersten Ergebnisplots: Anpassung Residual Umfangsfehler-Spanne (Punkt 7). Bitte später Zielband (z.B. ±0.02 m) nennen falls enger.

## 11. Nächste Schritte nach Review

- Einarbeiten Feedback → finalize config/model.yml
- decisions.log ergänzen
- Phase 2: Korrelationsvalidierung + Testplanung

Bitte Feedback / Korrekturen je Abschnitt (Nummer + Änderung). Falls „ok“, vermerken.
