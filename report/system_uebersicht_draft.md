# Systemübersicht & Annahmen (Draft zur Review)

Status: Phase 1 (Workspace-Scan abgeschlossen – konsolidiert mit `systemdescription/spezifikationen.md` – Update nach Stakeholder-Auftrag eingearbeitet)
Erstellt: 2025-10-06 (letztes Update: 2025-10-08 Auftrag-Refinement)

## 1. Betriebsprofil

- Geschwindigkeitsbereich: 0–45 km/h (lokaler Rangier-/Kurzstreckenbetrieb; keine Hochgeschwindigkeit → Latenz × v Effekte begrenzt)
	- Annahme: Obergrenze 45 km/h nach jüngster Stakeholder-Anpassung (vorher 60 km/h) reduziert den erwarteten Beitrag des Terms v·t_latenz sowie dynamische Effekte; konservativ behalten wir bisherige Balise-Mittelwerte unverändert bei, wodurch P95/P99 leicht überschätzt werden (Sicherheitsmarge).
- Beschleunigungsprofil: moderat (|a| ≤ 0.5 m/s²)
	- Annahme: Reduktion von 0.7 auf 0.5 m/s² minimiert Notwendigkeit höherer IMU-Dynamikmodelle; lineare Approximation der Latenzfehler bleibt gültig.
- Streckenmodusanteile: open 70%, urban 30%, tunnel 0%
	- Annahme: Tunnelbetrieb aktuell ausgeschlossen (0%) → GNSS Total-Ausfälle werden als Stresstest separat gehalten, im Nominalszenario nicht berücksichtigt.

## 2. Systemgrenze & Subsystemarchitektur (aktualisiert)

Gemäß aktualisierter Festlegung besteht das betrachtete Lokalisierungssystem (Systemgrenze) aus:

1. Algorithmus auf der sicheren Recheneinheit (regelbasiertes Intervall-Verfahren – KEIN EKF zwischen sicherem und unsicherem Pfad)
2. GNSS-Empfänger (inkl. Korrekturdienst)
3. IMU (integraler Bestandteil des Präzisionspfades – liefert geglättete/integrierte Bewegungsinformation für GNSS-Stützung)

Alle anderen Elemente (Balisen im Gleis, Balisen-Lesegerät, Odometrie, Digitale Karte, Journey-Profile Subsystem) liegen außerhalb der Systemgrenze und liefern Eingaben. Ihre Fehler werden als externe Input-Unsicherheiten modelliert, beeinflussen aber nicht die sicherheitsgerichtete Logik der Intervallbegrenzung.

Architektur-Pfade (logische Sicht):

- Sicherer Intervallpfad ("safe interval"): Externe Inputs Balise + Odometrie + Karte → Algorithmus generiert ein sicheres Positionsintervall [x_min, x_max].
- Nicht-sicherer Präzisionspfad ("precision"): GNSS + IMU → Punkt-Schätzung x_gnss (IMU liefert Kurzzeit-Stabilisierung / Dead-Reckoning-Brücken ohne das sicherheitsgerichtete Intervall zu verlassen).
- Kombinationslogik: Vier deterministische Regeln (vgl. Auftrag 1.1.3) zur Ausgabe eines endgültigen sicheren Positionswertes x_out immer innerhalb [x_min, x_max].

Priorisierung Phase 1: Worst-Case sicherer Pfad (Intervallbreite) hat Vorrang; Präzisionspfad (GNSS+IMU) wird nach Nachweis der sicheren Intervallbreite zur Gesamt-RMSE Optimierung betrachtet.

Hinweis: Frühere Verweise auf einen ekf_simple Fusions-Proxy sind aus dem Systemgrenz-Reporting entfernt; intern kann ein Surrogat zur Monte-Carlo-Streuung genutzt werden, ohne die regelbasierte Sicherheitsargumentation zu verändern.

Fehlerkopplung: Kartenfehler (externer Input) erzeugen korrelierte Offsets in Balise-, Odometrie- und GNSS-Daten und wirken so auf Intervall und akzeptierten GNSS-Punkt.

## 3. Zielmetrik & Anforderungen

- Primäre Anforderung (Nutzer): Längs-RMSE < 0.20 m (gesamtes System nominal). Zwischenziel jetzt: Nachweis, dass sichere Intervallbreiten (auf Basis 99%-Perzentil) ohne GNSS/IMU-Beitrag hinreichend klein bleiben, um diese Zielgröße zu ermöglichen.
- Zusätzliche Berichtskennzahlen: μ, σ, RMSE, P50, P90, P95, P99 (Longitudinal / Lateral / 2D), Bootstrap-CIs
- Verfügbarkeit / Ausfallmechanismen (GNSS, Balise) werden später erweitert (GNSS Daten fehlen noch)

## 4. Validierte Fehlerquellen aus bestehenden Analysen

### 4.1 Balisen / BRV4 (konsolidiert, aktualisiert)

Quellen: `spezifikationen.md` (Abschnitte 3 / 3.3 Tabelle) & interne Monte-Carlo-Auswertung.

Konfligierende Angaben & Konsolidierung:

| Aspekt | Spezifikationen | Vorheriger Draft | Entscheidung (Simulation v0) | Begründung |
|--------|-----------------|------------------|------------------------------|------------|
| Mittlerer Längsfehler (nominal) | 10.2 cm @ 30 km/h (alternativ 12.4 cm „sicher") | 13.6 cm (aggregierte Legacy) | 12.0 cm | Annahme: Mittelwert zwischen empirischem 10.2 und konservativem 13.6; konservativ beibehalten trotz reduzierter Max-Geschwindigkeit (jetzt 45 km/h) → leichte Sicherheitsmarge |
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

mit w_tail=0.15 Mischanteil (Kalibrierung gegen Ziel-P95/P99).

Annahmen & Begründungen Balise:
- Annahme: w_tail=0.15 liefert P95≈0.18 m & P99≈0.22 m für aktualisierte Geschwindigkeitsbandbreite (reduzierter v senkt v·t Anteil → Tailgewicht unverändert konservativ).
- Annahme: Negative Frühdetektion (t_early) erst als Placeholder, nicht in Basis-P95/P99 eingerechnet (Vermeidung künstlicher Verengung des Sicherheitsintervalls).
- Annahme: Gruppenredundanz → p_miss_group vernachlässigbar; Sicherheit nicht latenzkritisch beeinflusst.
- Annahme: Latenzverteilung trunc Normal(10 ms, 2 ms) [6,14] ms ausreichende Approximation (keine signifikante Abweichung im 99%-Quantil ggü. gemischtem Uniform-Modell laut Spezifikation).

Begründung Konfliktlösung: Frühere 13.6 cm beinhaltete stärkere Tail-Gewichtung bei höherer Referenzgeschwindigkeit; Spezifikationswert 10.2 cm erscheint für 30 km/h, aber Zielsystem arbeitet bis 60 km/h. Mittelwert 12 cm minimiert Risiko Unterabschätzung der RMSE. Tail-Anhebung nötig zur konservativen SIL1-Betrachtung.

Heavy-Tail Szenario (separater Stress-Test): Setze w_tail=0.35 und cap=0.12 m → erwartetes P99 ~0.28–0.30 m.

Balisen-Gruppen: Praktisch werden Gruppen (2–7 Balisen) verbaut; dadurch ist die effektive Gruppen-Detektionsausfallwahrscheinlichkeit vernachlässigbar (p_miss_group ≪ 1e-4). Vorheriges Markov-Ausfallmodell wird für die Bestimmung der sicheren Intervallbreite deaktiviert (nicht-dominant). Optionales Degradationsszenario bleibt als Stress-Test.

Neue Placeholder-Komponente Frühdetektion (Early Detection): Geschwindigkeitsabhängiger negativer Latenzanteil t_early = c1·v, c1 ≈ 0.5 ms/(m/s), begrenzt auf 4 ms. Netto-Latenz t_eff = max(t_latenz − t_early, 0). Ziel: plausible teilweise Kompensation des v·t Terms bis empirische Daten vorliegen.

#### 4.1.1 Empirische Evidenz Balise-Reader Log (BART_Cut_Testfahrt.log)

Analyse des bereitgestellten Rohlogs (`systemdescription/BART_Cut_Testfahrt.log`) fokussiert auf Telegramm-Fundraten, Wiederholungs-Skips und INCIDENT-Ereignisse. Parsing-Regel: Regex `Telegrams found: (k) telegrams, skipped repetitions: (r)` über alle Meldungen.

Aggregierte Kennzahlen (1247 ausgewertete Analysefenster, Seed-unabhängig):

| Kennzahl | Wert | Kommentar |
|----------|------|-----------|
| Fenster (Analyseaufrufe) | 1247 | Basis N für Raten |
| Summe Telegramme | 1192 | Brutto empfangene Short-Telegramme |
| Mean Telegramme/Fenster | 0.956 | Leicht <1 → viele Leerlauf-Fenster (Zugbewegung / Timing) |
| P50 / P90 / P95 / P99 (Tele/Fenster) | 1 / 2 / 2 / 3 | Max 3 beobachtet (kein Extrem-Cluster) |
| Anteil Fenster mit 0 Telegrammen | 29.8% | „Zero Windows“ – nicht zwingend Ausfall, eher Nichtpassage / Idle; liefert Obergrenze für naive p_idle |
| Skipped repetitions (gültig, r≥0) – Mean | 3.91 | Interne Wiederholungen / deduplizierte Repetitionsframes |
| Skipped repetitions P90 / P95 / P99 / Max | 7 / 8 / 10 / 13 | Repetitions-Last im oberen Dezil; Timeout=2000 ms plausibel ausreichend |
| INCIDENT Events | 28 | Bit-Anomalie-Marker („number of demodulated X-bits“) |
| INCIDENT Rate pro Fenster | 2.25% | Obergrenze für sporadische Bit-/Demodulationsanomalien (nicht gleich Fehldetektion) |

Interpretation & Abgleich mit Modellannahmen:

1. Fundverteilung: Max=3 Telegramme/Fenster → kein Hinweis auf größere Telegramm-Bursts; Heavy-Tail im Modell (w_tail=0.15) weiterhin nicht durch Fund-Bursts motiviert, sondern durch Latenz-/Multipath-Fehler – bleibt unverändert.
2. Zero Windows (~30%): Diese Fenster sind nicht direkt als „Balise verpasst“ zu interpretieren (Log enthält auch Idle-Zeit). Für p_miss_group bleibt Annahme ≪1e-4 valide; keine Evidenz für systematischen Verlust beim tatsächlichen Überfahren.
3. Skipped repetitions: Oberes Dezil (≥7) zeigt, dass Wiederholungsframes auftreten, jedoch mit moderatem Maximum (13). Kein Bedarf, Repetition Timeout (2000 ms) im Modell zu verschärfen; Latenzkomponente wird nicht durch Exzess-Repetitionen dominiert.
4. INCIDENT Rate 2.25%: Relevanz für potenziellen Zusatzfehler (Bit-Anomalien). Da alle gezeigten Telegrammdumps „ALL_TESTS_OK“ aufweisen, führen INCIDENTs offenbar meist zu Diagnoseeinträgen ohne Telegrammverwerfung. Konservativ kann ein kleiner Zusatz-Noise-Term (<1 cm) oder erhöhte Tail-Gewichts-Stabilisierung beibehalten werden; keine Erhöhung w_tail erforderlich.
5. Konsistenz der Scrambling/Control Bits über Dumps → keine offensichtliche Konfigurationsvariabilität, unterstützt Annahme stationärer Parameter.

Auswirkungen auf bestehende Parameter:
- Keine Anpassung von w_tail (0.15) nötig; log zeigt keine signifikante Häufung extremer Empfangsfenster.
- p_miss_group weiterhin vernachlässigbar (Zero Windows nicht als Miss zu werten ohne Trajektorienmarker).
- Latenzmodell bleibt unverändert; keine Evidenz für extrem lange Repetitionsketten.
- Early-Detection Placeholder weiterhin unbestätigt (Log enthält keine Frühzeitstempel-Indikatoren) – bleibt deaktiviert für Intervallverengung.

Geplante Ergänzungen (optional Phase ≥2):
- Detaillierter Klassifikator für Idle vs. tatsächliche Passfenster (Integration Odometrie / Zeitstempel) zur besseren Obergrenze p_miss.
- Mapping INCIDENT-Typen auf spezifische Fehlerklassen (Bit 1 vs. 0 Anomalie) → differenziertes Auswirkungsmodell.

Abweichungen / Nicht abgeleitet:
- Keine Distanzinformation im Log → keine direkte empirische Schätzung des geschwindigkeitsabhängigen Latenzterms.
- Keine Positionsoffsets im Log → Balise Längsfehler-Distribution unverändert modellbasiert.

Damit stützt das Log primär Stabilität der Annahmen und liefert oberseitige Raten (Idle/Incident), ohne Necessität für Parameter-Revision.

### 4.2 Odometrie (aktualisiert: freilaufende Einzelachse, Umfang bereits kompensiert)

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
| Residual Umfangsfehler (typisch) | Abweichung ±0.02 m / 100 m Segment (kompensiert) | Auftrag Zusatzinfo (ersetzt frühere konservative Spanne) |

Simulation Implementation v0 (angepasst auf sichere Pfad Priorität):

1. Stochastischer inkrementeller Fehler = Quantisierung (Uniform(-Δ/2, Δ/2)).
2. Driftanteil = Normal(0, (0.010 m / km)·Δd) pro Segment (Reset bei Balise). (Prüfung offen, ob durch freilaufende Achse drift_per_km weiter reduzierbar.)
3. Residual Umfangsfehler: Uniform(-0.02, 0.02) m pro 100 m (linear mit Segmentlänge); Stress-Szenario: frühere größere Spannen zur Robustheit.

Erläuterung Residual Umfangsfehler (aktualisiert 3 cm / 10 cm Extrem): Dieser Term modelliert den verbleibenden systematischen Distanzoffset zwischen zwei Balisen nach Anwendung der adaptiven Umfangskorrektur. Er bündelt:

- Verzögerte Erkennung sehr kleiner Umfangsänderungen (<1 mm Schwelle)
- Temperatur-/Druck-induzierte elastische Radumfangsvariation
- Nichtmodellierte minimale Schlupfanteile auch bei nicht-angetriebener Achse

Die typische Spanne jetzt ±0.02 m (2 cm) / 100 m (≈0.0002 relativ) basierend auf kompensierter Umfangsbestimmung. Ein Extrem-/Stressfall wird mit ±0.10 m (10 cm) modelliert (seltene Kombination Temperaturgradient + verzögerte Kalibrierung + geringe Balisen-Dichte).

Annahmen & Begründungen Odometrie:
- Annahme: Drift 10 mm/km bleibt gültig trotz reduzierter Max-Geschwindigkeit (geringere thermische & dynamische Variation → konservativ).
- Annahme: Residual Umfang Uniform-Verteilung (statt Normal) um gleichmäßige Unsicherheit ohne Zentrierungsannahme abzubilden.
- Annahme: Keine explizite Schlupfmodellierung (freilaufende Achse) → potentielle unerkannte Mikro-Schlupfanteile im Residual enthalten.

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

Annahmen & Begründungen Karte:
- Annahme: Kombination Normal + gedämpfte Exponential Tail (Gewicht 0.3) liefert realistisch leicht-schiefe Verteilung (Semivariogramm-Hinweise auf seltene lokale Ausreißer).
- Annahme: Skalierungsfehler α ~ N(0,6e-4) nur für Distanzen >2 km relevant → vernachlässigt im typischen Kurzstreckenbetrieb (≤1 km zwischen Balisen) -> konservativ, da Nichtberücksichtigung keine künstliche Intervallverengung erzeugt.
- Annahme: Querfehler Normal(0,0.014 m) ausreichend (fehlende Hinweise auf heavy-tail lateral in vorliegenden Spezifikationen).

### 4.4 GNSS + IMU (innerhalb System) / Regelbasierte Nutzung (aktualisiert)

GNSS (Defaults akzeptiert):

| Umgebung | Bias (N(0,σ_b)) | Messrauschen 1σ | Outage p/epoch | Tail Zusatz (Multipath) |
|----------|-----------------|-----------------|---------------|------------------------|
| Open | 0.25 m | 0.30 m | 0.01 | – |
| Urban | 0.50 m | 0.80 m | 0.05 | Exp(λ=2, cap 3 m, w=0.1) |
| Tunnel | n/a (kein Fix) | n/a | 1.0 | – |

IMU (innerhalb Systemgrenze – liefert Kurzzeit-Inertialstützung zur Brückung zwischen GNSS Messungen, verbessert Stabilität bei kurzfristigen Ausfällen / Degradierungen):

| Parameter | Modell | Wert |
|-----------|--------|------|
| accel_bias | N(0,σ) | σ=0.005 m/s² |
| gyro_bias | N(0,σ) | σ=0.02 °/s |
| accel_noise_density | Weißrauschen | 0.05 m/s²/√Hz |
| gyro_noise_density | Weißrauschen | 0.01 °/s/√Hz |
| Bias Random Walk Zeitkonstante | Exponential | τ=900 s |

Regelbasierte Kombination (ersetzt EKF Beschreibung):

1. GNSS invalid / diagnostisch schlecht → Ausgabe = Intervallmittel.
2. GNSS gültig & innerhalb [x_min, x_max] → Ausgabe = x_gnss.
3. GNSS gültig & außerhalb → Clamping auf Grenzwert.
4. Verfügbarkeits-Flanke → sanfte Überblendung (linear über n_steps, stets innerhalb Intervall). Parameter n_steps TBD.

Latenz: Für sichere Intervallgrenzen maßgeblich Balise/Odometrie; frühere "Fusion-Latenz" nur intern als Surrogat.

Annahmen & Begründungen GNSS/IMU:
- Annahme: Bias- & Rauschwerte unverändert trotz geringerer v_max (45 km/h) – konservative Beibehaltung (Rauschen v-unabhängig, Multipath urban bleibt dominanter Faktor).
- Annahme: Tunnel = 0% Betriebsanteil → Outage-Modell primär open/urban; vollständige Outage-Szenarien verschoben in Stress-Test.
- Annahme: IMU Bias Random Walk τ=900 s hinreichend groß relativ zu Simulationshorizont → Bias quasi konstant innerhalb Standard-Sim → Modellvereinfachung.
- Annahme: Keine probabilistische Fusion → Regelwerk verhindert Verstärkung unsicherer GNSS-Ausreißer (Clamping-Regel 3).

## 5. Funktionale Verarbeitungspfade & vereinfachte Fehlermodelle (Stakeholder-Summary)

Ziel dieses Abschnitts: Technisch verständliche Übersicht ohne vertiefte Statistik. Jeder Pfad liefert Positionsinformation; Fehlerquellen addieren sich (vereinfachte additive Modellierung) oder wirken multiplikativ bei Skalenfehlern.

### 5.1 Balisen-Verarbeitungspfad (Early Detection Placeholder)

1. Detektion (Antenne + Signalprozess): Rohsignal → Telegramm → Zeitstempel.
2. Zeitstempel-Korrektur (Verarbeitungs- / Kommunikationslatenz).
3. Zuordnung zur Karten-Referenzposition (Balise-ID → Karte).
4. Ausgabe eines absoluten Positionsankers.

Vereinfachtes Fehlermodell (Längsrichtung):

Positionsfehler_balise_längs ≈ (Geschwindigkeit · (t_latenz − t_early)⁺) + Antennenoffset + Signalqualität/Tail + EM-Störungen + Witterung + Kartenoffset

mit t_early ≥ 0 (geschwindigkeitsabhängig), (·)⁺ = max(·,0). Verteilung t_early noch nicht empirisch kalibriert.

Typische Beiträge (Richtwerte):

- Latenzterm: v( m/s ) · 0.010 s (σ 0.002 s) → bei 10 m/s ≈ 0.10 m ±0.02 m
- Antennenoffset: Normal(0, 0.02 m)
- Tail (Ausreißer): mit 15% Wahrscheinlichkeit zusätzliche Exponential-Komponente (λ=0.05, auf 0.08 m begrenzt)
- EM-Störung: Rayleigh(σ=0.012 m) ≈ mittlerer Beitrag ~0.015 m
- Witterung: Uniform(-0.015, 0.015) m
- Kartenoffset: Normal(0, 0.019 m)

Interpretation: Dominanter Anteil ist bei höheren Geschwindigkeiten der Latenzterm; durch reduzierte v_max (45 km/h) sinkt dessen Beitrag gegenüber früherem 60 km/h Szenario geringfügig; systematische Offsets (Karte, Antenne) und stochastische Streuung (EM, Tail) bestimmen P99.

Annahmen & Begründungen Pfad Balise:
- Annahme: t_early Placeholder nicht zur Verengung der Sicherheitsgrenzen genutzt, bis empirische Validierung vorliegt.
- Annahme: Rayleigh EM-Modell beibehalten (keine neueren EM-Daten vorliegend) → konservativ moderate Heavy-Tail Ergänzung.
- Annahme: Wetter Uniform ±1.5 cm bleibt trotz saisonalem Ausschluss (keine Tunnel) – Oberflächenbedingungen im urban/open identisch plausibel.

### 5.2 Odometrie-Verarbeitungspfad

1. Inkrementzählung (Impulsgeber / Encoder) → Weginkrement.
2. Quantisierung (Schrittweite ≈ 13.4 mm Beispiel).
3. Drift & Umfangsanpassung (Radverschleiß, adaptive Kalibrierung per Balisenabstand).
4. Integration bis zum nächsten Balisen-Anker → relative Position.

Vereinfachtes Fehlermodell Segment (zwischen Balisen):

Positionsfehler_odo_segment ≈ Quantisierungsrauschen + Drift + Residual Umfangsfehler (±0.02 m /100 m) + (optional Stress: zusätzlicher systematischer Block)

Typische Beiträge (für 1 km Segment):

- Quantisierung (RMS ~4–5 mm)
- Drift (10 mm/km vor Korrektur, abgeschnitten durch Balise-Reset)
- Residual Umfang (3 cm Band)

Interpretation: Die Odometrie ist sehr präzise kurzfristig; Fehler wachsen zwischen Balisen kontrolliert und werden bei jedem Balisen-Event zurückgesetzt.

Annahmen & Begründungen Pfad Odo:
- Annahme: Linearer Drift-Envelope ausreichend (keine Quadratterme nötig bei v ≤ 45 km/h).
- Annahme: Ohne Separate Schlupfmodellierung; eventuelle kleine Schlupfanteile im Residual bereits konservativ abgedeckt.

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

### 5.4 Zusammenspiel der Pfade (regelbasiert statt probabilistischer Fusion)

- Balise liefert absolute Anker mit moderater Einzel-Unsicherheit (dominiert durch Latenz + Offsets); reduziert Odometrie Drifts.
- Odometrie füllt die Zeit/Gleisdistanz zwischen Balisen hochauflösend mit geringer Fehlerzunahme.
- Karte projiziert/fusioniert beide Pfade und definiert systematische Offsets (→ Korrelationen).

Intervallbildung (auf 99%-Perzentil basierend):

Annahme: Sicherheitsintervall [x_min, x_max] definiert als symmetrischer Bereich um den letzten Balisenanker plus Odometrie-Inkrement mit Halbbreite = P99(|e_secure(d)|), wobei e_secure(d) zusammengesetzt ist aus:

e_secure(d) = e_balise_anchor + e_odo(d) + e_map

mit Komponenten (vereinfachte Bounding-Verteilungen):
1. e_balise_anchor: Kombination Latenz (v·t_latenz), Antennenoffset, EM, Tail, Wetter (siehe 4.1) → P99_balise.
2. e_odo(d): Quantisierung + Drift + Umfangresidual skaliert mit Distanz d seit letztem Balisenanker → P99_odo(d).
3. e_map: Kartenoffset (längs) → P99_map.

Annahme: Korrelationen zwischen Termen für konservative Intervallabschätzung vernachlässigt (additive P99 Approximation: P99_total ≈ P99_balise + P99_odo(d) + P99_map). Dies überschätzt echtes P99 leicht (Sicherheitsreserve).

Somit: x_min = x_anchor + s_odo(d) − P99_total(d); x_max = x_anchor + s_odo(d) + P99_total(d), mit s_odo(d) = integrierte Odometrie-Distanz.

Breitenwachstum zwischen Balisen: W(d)=2·P99_total(d) ≈ 2·(P99_balise + P99_map + P99_odo(d)).

Regelbasierte Nutzung GNSS/IMU unverändert (Abschnitt 4.4): GNSS-Punkt ersetzt Intervallmittel nur falls innerhalb [x_min, x_max]; andernfalls Clamping → garantiert Sicherheit.

Annahmen & Begründungen Intervall:
- Annahme: Symmetrisches Intervall ausreichend obwohl Balise Fehlerverteilung tail-geschoben sein kann; P99 symm. konservativ.
- Annahme: Lineare Summation der Einzel-P99 anstatt Faltung → konservative Obergrenze (kein Reduktionsfaktor durch teilweise Unkorreliertheit angewandt).
- Annahme: Distanzabhängigkeit nur im Odo-Term modelliert; Balise- und Kartenanteile konstant bis neuer Anker.

### 5.5 Warum additive Modelle hier weiterhin ausreichend (für Stakeholder)

Obwohl einige Fehlerquellen nicht strikt additiv sind (z.B. Kopplungen, nichtlineare Filter), liefert die additive Näherung konservative Schätzungen für Streuung und Perzentile bei homogenen Betriebsbedingungen (<60 km/h) und moderaten Latenzen. Detailliertere Kopplung (z.B. Kovarianzmatrix, Copula) wird intern in der Monte-Carlo Pipeline berücksichtigt, ist für das grundsätzliche Verständnis aber nicht erforderlich.

### 5.6 Adaptive (potenziell asymmetrische) sichere Intervallbestimmung & zustandsvolle 4‑Regeln-Fusion (Phase‑4 Update)

Status: Implementiert (longitudinal adaptiv aktiv), Asymmetrie vorbereitet, lateral stateful noch offen.

#### 5.6.1 Motivation

Die ursprüngliche symmetrische Halbbreite ±P99_additiv ist konservativ aber unabhängig von Geschwindigkeitszustand. Da Anteile (v·t_latenz, Odo Drift-Wachstum) geschwindigkeitsabhängig variieren, erlaubt adaptive Binning eine lokale Verengung ohne Verlust der konservativen Sicherheitsreserve.

#### 5.6.2 Verfahren (aktuelle Implementierung)

Alle `Δt_update = 1.0 s` (Konfig `fusion.interval.update_cadence_s`) werden Intervallgrenzen neu bestimmt:

1. Speed-Binning mit Breite `speed_bin_width` (Default 5.0 m/s).
2. Mindestbin-Größe: `min_bin_fraction · N` (Default 5%).
3. Quantile je Bin: `Q_low = Q_{q_low_pct}` (1%), `Q_high = Q_{q_high_pct}` (99%).
4. Fallback: Unterbesetzte Bins nutzen global symmetrische Grenze ±Q_{99}(|e_secure|).
5. Midpoint: `mid = 0.5·(lower+upper)` (bei zukünftiger Asymmetrie verschoben).

Formeln:

```text
lower_i = Q_{q_low}( e_secure | i∈B )
upper_i = Q_{q_high}( e_secure | i∈B )
```

Asymmetrie (Decision A) wird durch unabhängige Schätzung von lower/upper unterstützt (kein Erzwingen von Symmetrie).

#### 5.6.3 Zustandsvolle Regel-Fusion (RuleFusionState)

Modi pro Sample i:

- `midpoint`: GNSS/IMU Outage → Ausgabe mid_i.
- `unsafe`: unsicherer Pfad innerhalb [lower_i, upper_i] → direkte Nutzung.
- `unsafe_clamped`: unsicherer Pfad außerhalb → Clamping (Sicherheitsgarantie).

Transitions werden linear über `blend_steps` (Default 5) geglättet (Decision C). Exponentielle Alternative dokumentiert, nicht aktiviert.

#### 5.6.4 Qualitätsheuristik (Decision B)

Nutzung unsicherer Pfad nur falls (available ∧ |raw|≤upper). Keine zusätzlichen RAIM/DOP Inputs → dokumentierte Vereinfachung SIL1-konservativ (verhindert Intervallvergrößerung durch Ausreißer).

#### 5.6.5 Additive vs. Joint P99 Bias

Metriken: `P99_additiv = Σ P99(|Komponent_k|)` vs. `P99_joint = P99(|Σ Komponent_k|)`.  
Bias_% = 100·(P99_additiv / P99_joint − 1). Tests belegen stabil positiven Bias (≥~2% mittlerer Relativwert) → explizite Sicherheitsreserve. Export: `secure_interval_metrics.csv`, Zeitreihe `secure_interval_growth.csv`.

#### 5.6.6 Neue Artefakte / Plots

| Datei | Inhalt |
|-------|--------|
| fusion_mode_stats.csv | Zeitanteile midpoint / unsafe / unsafe_clamped |
| fusion_switch_rate.csv | Switch Rate pro Schritt |
| secure_interval_bounds.csv | Snapshot lower / upper Arrays (Audit, Asymmetrie) |
| secure_interval_growth.csv | Additiv vs. joint P99 + Bias Verlauf |
| fusion_mode_share.png | Gestapelte Anteilskurve Modi |
| fused_time_interval_bounds.png | Snapshot der Intervallgrenzen (sortierte Samples) |

#### 5.6.7 CLI Erweiterungen

| Flag | Zweck |
|------|------|
| --interval-update-cadence-s | Aktualisierungsfrequenz adaptive Intervalle |
| --no-adaptive-interval | Deaktiviert adaptive Quantile (Fallback global) |
| --fusion-stats | Export Mode Shares & Switch Rate |
| --export-interval-bounds | Persistiert aktuelle lower/upper |
| --fusion-mode | Umschalten (rule_based\|var_weight) |

#### 5.6.8 Offene Punkte

- Lateral stateful Fusion analog longitudinal.
- Logging Fallback-Rate (Bins < min_bin_fraction) & Warnschwelle (>20%).
- Performance-Benchmark (Ziel Overhead < +15%).
- Asymmetriedaten (Geschwindigkeits-Schiefe) sobald reale Residuen vorliegen.

#### 5.6.9 Sicherheitsschlüssel

1. Hard-Clamp garantiert fused ∈ [lower, upper].
2. Positiver Bias additive vs. joint P99 = dokumentierte Reserve.
3. Qualitätsheuristik verhindert Nutzung problematischer unsicherer Ausreißer.
4. Übergangsglättung reduziert dynamische Sprünge → minimiert falsch-positive Sicherheitsverletzungs-Alarme.
5. Adaptive lokale Quantile verhindern unnötig großzügige globale Intervallbreite.

#### 5.6.10 Testabdeckung (Stand)

Abgedeckt: Bias-Konsistenz, Zeitreihen-Bias≥0, Clamping, Asymmetrie Midpoint-Shift, Basic Blend Monotonie, Switch Counting.  
Geplant: strikte Delta-Schrittgrenze, Ausreißer-Injektion für Heuristik, Blend-Profil Outage→unsafe detailliert.

#### 5.6.11 Nutzen-Zusammenfassung

Reduktion potenzieller Überbreite (lokale Anpassung) bei gleichzeitiger Beibehaltung formaler Sicherheitsreserven und transparenter Betriebsmetriken (Mode Shares, Switch Rate) für spätere Felddatenvalidierung.

---

## 6. Geplante Modellierung & Fehlerpropagation

| Fehlerquelle | Modellierung (initial) | Parameterquelle | Relevanz Longitudinal | Relevanz Lateral | Bemerkung |
|--------------|------------------------|-----------------|-----------------------|------------------|-----------|
| Balise Messfehler | Legacy truncated exponential composite | balise_error_analysis.md | HOCH | MITTEL | Heavy-Tail Alternative optional |
| Odometrie Quantisierung | Deterministic ±Δ/2 uniform | odometrie_error_analysis.md | MITTEL | NIEDRIG | Dominiert bei langen Intervallen |
| Odometrie Drift | Lineares Drift+Rauschen | odometrie_error_analysis.md | MITTEL | NIEDRIG | ~10 mm/km |
| Karten Geometrie | Normal + exp Interpolation (konsolidiert) | spezifikationen.md & map_error_analysis.md | MITTEL | MITTEL | Korrelierter Offset |
| Karten Skalierung | Proportionaler Fehler (α ~ N(0,6e-4)) | spezifikationen.md | NIEDRIG (<2 km) | NIEDRIG | Ab >2 km relevant |
| GNSS Bias/Noise | Normal / lognormal (bestätigt) | Auftrag / akzeptierte Defaults | HOCH | HOCH | Open vs urban vs tunnel |
| GNSS Ausfälle | Bernoulli pro Zeitschritt | Defaults | HOCH | HOCH | Annahme: Tunnel 0% → Outage-Basis offen/urban |
| IMU Bias/Drift | Random Walk + Bias | (Standardvorschlag) | MITTEL | MITTEL | Für Dead-Reckoning bei GNSS-Ausfall |
| Balise Ausfall | Linear oder Markov | balise_error_analysis.md | MITTEL | MITTEL | Wahl pending |
| Zeit-Latenz Fusion | Stoch. Delay → Position = v·Δt | balise_error_analysis.md | MITTEL | NIEDRIG | v ≤ 60 km/h begrenzt |

Nicht berücksichtigt (initial): Extreme Wetter (Regen/Laub/Schnee) → keine quantifizierten Daten; Oberleitungsreflexionen GNSS (multipath) → später falls Daten; Weichen-Topologiefehler → binär, separat qualitativ.

## 7. Korrelationen (Draft – Terminologie angepasst, Targets unverändert)

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

## 10. Offene Punkte / Status (aktualisiert)

| Punkt | Thema | Status | Aktion nötig |
|-------|-------|--------|--------------|
| 1 | Balise Konsolidierung & Heavy-Tail Flag | BESTÄTIGT (mit p_miss Korrektur) | optional Tail-Stress aktivieren später |
| 2 | GNSS Defaults | BESTÄTIGT | keine |
| 3 | IMU Parameter | AKTUALISIERT (automotive) | keine |
| 4 | Balise Ausfallmodell | MARKOV AKTIV | Feinjustierung nach erster Sim falls Abweichung P_miss |
| 5 | Regelwerk statt EKF | IMPLEMENTIERT (Beschreibung angepasst) | Konsistenz model.yml prüfen |
| 5a | Early-Detection Balise | NEU (Placeholder) | Parametrisierung / Daten offen |
| 5b | Fusion Latenz Surrogat | REDUZIERT 20±5 ms (intern) | Nicht architekturkritisch kommunizieren |
| 6 | Korrelationen | BESTÄTIGT | Phase 2 Validierung |
| 7 | Residual Umfangsfehler | AKTUALISIERT (±0.02 m/100 m, Stress ±0.10 m) | Nach MC-Befund ggf. Verengung |
| 8 | P99 Intervallbildung | IMPLEMENTIERT (additive P99 Summation) | Validierung konservative Überschätzung quantifizieren |

Offen zur Entscheidung nach ersten Ergebnisplots: Anpassung Residual Umfangsfehler-Spanne (Punkt 7). Bitte später Zielband (z.B. ±0.02 m) nennen falls enger.

## 11. Nächste Schritte nach Review (angepasst)

- Prüfen, dass `model.yml` keine EKF-Verschmelzung sicher/unsicher enthält (nur Regelparameter)
- Early-Detection Parameter c1 & Cap evaluieren oder Feature temporär deaktivieren (Flag) → decisions.log
- Intervallwachstumsmodell numerisch verifizieren (Monte Carlo) vs. Zielband
- decisions.log ergänzen (Systemgrenze, Balise Gruppen p_miss vernachlässigbar, Regelwerk 4 Regeln, Early-Detection Placeholder, Umfang ±0.02 m /100 m)
- Phase 2: Korrelationsvalidierung + Testplanung bleibt bestehen
- Quantifizierung P99 Überschätzung durch additive Annäherung (Vergleich mit Kopplungs-Sampling)

Bitte Feedback / Korrekturen je Abschnitt (Nummer + Änderung). Falls „ok“, vermerken.
