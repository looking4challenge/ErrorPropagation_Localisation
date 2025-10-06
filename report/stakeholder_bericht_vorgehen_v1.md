# Fehlerfortpflanzung in Lokalisierungssystemen für Schienenfahrzeuge

## Methodisches Vorgehen und Fehleranalyse

**Projekt:** ErrorPropagation_Localisation  
**Erstellt:** 6. Oktober 2025  
**Status:** Vorläufiger Bericht zur Stakeholder-Abstimmung  
**Sicherheitskontext:** SIL1-relevante Lokalisierung

---

## Zusammenfassung

Dieser Bericht beschreibt das methodische Vorgehen zur systematischen Analyse der Fehlerfortpflanzung in hybriden Lokalisierungssystemen für Schienenfahrzeuge. Das Ziel ist die quantitative Bewertung der Positionsgenauigkeit unter Berücksichtigung aller relevanten Fehlerquellen und deren Wechselwirkungen mittels Monte-Carlo-Simulation.

Das untersuchte System kombiniert sichere (Balisen, Odometrie, digitale Karte) und nicht-sichere Lokalisierungspfade (GNSS, IMU) zur präzisen Positionsbestimmung im Geschwindigkeitsbereich 0-60 km/h. Die Analyse fokussiert auf longitudinale Positionsgenauigkeit mit der Zielanforderung RMSE < 0.20 m im nominalen Betrieb.

---

## Inhaltsverzeichnis

### 1. Einleitung und Zielsetzung
1.1 Problemstellung und Motivation  
1.2 Systemkontext und Sicherheitsanforderungen  
1.3 Methodischer Ansatz  
1.4 Abgrenzung und Annahmen  

### 2. Systemarchitektur und Betriebsprofil
2.1 Hybride Lokalisierungsarchitektur  
2.2 Sicherer vs. nicht-sicherer Pfad  
2.3 Betriebsparameter und Einsatzszenarien  
2.4 Fusionsansatz und Datenverarbeitung  

### 3. Informationsverarbeitungspfade
3.1 Balisen-basierte Lokalisierung  
3.2 Odometrische Positionsbestimmung  
3.3 Digitale Karten-Referenzierung  
3.4 GNSS-gestützte Positionierung  
3.5 IMU-basierte Trägheitsnavigation  

### 4. Fehlermodellierung und -quantifizierung
4.1 Systematische Fehleridentifikation  
4.2 Stochastische Fehlermodelle  
4.3 Korrelationen zwischen Fehlerquellen  
4.4 Zeitabhängige Fehlerfortpflanzung  

### 5. Monte-Carlo-Simulationsansatz
5.1 Simulationsarchitektur  
5.2 Parametrisierung und Konfiguration  
5.3 Validierungsstrategien  
5.4 Sensitivitätsanalyse  

### 6. Erwartete Ergebnisse und Bewertungskriterien
6.1 Zielmetriken und Kennzahlen  
6.2 Statistische Auswertung  
6.3 Visualisierung und Reporting  

### 7. Implementierung und Reproduzierbarkeit
7.1 Software-Architektur  
7.2 Konfigurationsmanagement  
7.3 Qualitätssicherung  

### 8. Zeitplan und Ressourcenbedarf

---

## 1. Einleitung und Zielsetzung

### 1.1 Problemstellung und Motivation

Moderne Schienenfahrzeuge setzen zunehmend auf hybride Lokalisierungssysteme, die multiple Sensormodalitäten zur präzisen Positionsbestimmung kombinieren. Die Genauigkeit der resultierenden Positionsschätzung hängt dabei von der komplexen Wechselwirkung verschiedener Fehlerquellen ab, deren isolierte Betrachtung nicht ausreicht.

Die systematische Analyse der Fehlerfortpflanzung ist essentiell für:
- Nachweis der Erfüllung von Genauigkeitsanforderungen (RMSE < 0.20 m longitudinal)
- Identifikation kritischer Fehlerquellen und Optimierungspotentiale
- Robustheitsbewertung unter verschiedenen Betriebsbedingungen
- Validierung von Sicherheitsanforderungen im SIL1-Kontext

### 1.2 Systemkontext und Sicherheitsanforderungen

Das analysierte Lokalisierungssystem operiert im SIL1-Sicherheitskontext für lokalen Rangier- und Kurzstreckenbetrieb mit folgenden Charakteristika:

**Betriebsprofil:**
- Geschwindigkeitsbereich: 0-60 km/h
- Beschleunigungsbereich: |a| ≤ 0.7 m/s²
- Streckenverteilung: 70% offene Strecke, 25% urban, 5% Tunnel
- Einsatzdauer: kontinuierlicher Betrieb mit hoher Verfügbarkeit

**Sicherheitsrelevante Anforderungen:**
- Longitudinale Positionsgenauigkeit als primäre Zielmetrik
- Fail-safe Verhalten bei Sensorausfällen
- Nachweisbare Fehlererkennung und -behandlung
- Rückverfolgbare Konfiguration und Parametrierung

### 1.3 Methodischer Ansatz

Die Fehlerfortpflanzungsanalyse basiert auf einem Monte-Carlo-Simulationsansatz mit folgenden Kernprinzipien:

1. **Systematische Fehlermodellierung:** Jede relevante Fehlerquelle wird durch geeignete statistische Verteilungen charakterisiert
2. **Korrelationsberücksichtigung:** Wechselwirkungen zwischen Fehlerquellen werden über Korrelationsmatrizen modelliert
3. **Zeitdynamische Simulation:** Fehlerfortpflanzung wird über realistische Zeithorizonte simuliert
4. **Statistische Robustheit:** Ausreichend hohe Stichprobenzahlen für stabile Perzentilschätzungen
5. **Sensitivitätsanalyse:** Systematische Variation von Parametern zur Identifikation kritischer Faktoren

### 1.4 Abgrenzung und Annahmen

**Berücksichtigte Aspekte:**
- Quantifizierbare technische Fehlerquellen mit messbarer Positionswirkung
- Normale Betriebsbedingungen und definierte Degradationsmodi
- Sensorausfälle mit statistisch belegbaren Ausfallraten
- Umgebungseinflüsse mit parametrisierbaren Modellen

**Nicht berücksichtigt:**
- Extreme Wetterereignisse ohne quantifizierte Datenbasis
- Organisatorische und administrative Aspekte
- Seltene Systemfehler ohne statistische Relevanz
- Cyber-Security-Aspekte und Manipulationsszenarien

---

## 2. Systemarchitektur und Betriebsprofil

### 2.1 Hybride Lokalisierungsarchitektur

Das Lokalisierungssystem implementiert eine hybride Architektur mit redundanten Informationsquellen zur robusten Positionsbestimmung:

```text
┌─────────────────┐   ┌─────────────────┐
│  Sicherer Pfad  │   │ Erweiterer Pfad │
├─────────────────┤   ├─────────────────┤
│ • Balisen       │   │ • GNSS          │
│ • Odometrie     │◄─►│ • IMU           │
│ • Digitale Karte│   │ • Fusion-Proxy  │
└─────────────────┘   └─────────────────┘
         │                     │
         └───────┬─────────────┘
                 ▼
        ┌─────────────────┐
        │ Zentrale Fusion │
        │ (EKF-basiert)   │
        └─────────────────┘
                 ▼
        ┌─────────────────┐
        │ Positionsausgang│
        │ (x, y, σ, t)    │
        └─────────────────┘
```

### 2.2 Sicherer vs. nicht-sicherer Pfad

**Sicherer Pfad (SIL1-relevant):**
- **Balisen (BRV4):** Ereignis-getriggte absolute Positionsanker mit Referenz zur digitalen Karte
- **Odometrie:** Zwei-Achsen-System an nicht-angetriebener, nicht-gebremster Achse zur Schlupfminimierung
- **Digitale Karte:** Präzise Gleisgeometrie und Referenzpunkte als Projektionsbasis

**Nicht-sicherer Pfad (Präzisionserweiterung):**
- **GNSS:** Satellitennavigation mit umgebungsabhängiger Verfügbarkeit
- **IMU:** Trägheitssensoren zur Überbrückung von Sensorausfällen
- **Fusions-Proxy:** Vereinfachter EKF zur Sensordatenkombination

### 2.3 Betriebsparameter und Einsatzszenarien

Die Lokalisierungsgenauigkeit variiert signifikant mit den Betriebsbedingungen:

| Umgebung | Anteil | GNSS-Verfügbarkeit | Balisen-Dichte | Charakteristische Herausforderungen |
|----------|--------|-------------------|----------------|-------------------------------------|
| **Open** | 70% | Hoch (~99%) | Standard | Minimale Abschattung, optimale Sensorperformance |
| **Urban** | 25% | Reduziert (~95%) | Erhöht | Multipath, elektromagnetische Störungen |
| **Tunnel** | 5% | Nicht verfügbar | Maximal | GNSS-Ausfall, reduzierte Kommunikation |

### 2.4 Fusionsansatz und Datenverarbeitung

Die zentrale Fusion implementiert einen vereinfachten Extended Kalman Filter (EKF) mit folgenden Eigenschaften:

- **Zustandsvektor:** Position (x,y), Geschwindigkeit (vx,vy), Beschleunigung (ax,ay)
- **Prädiktionsmodell:** Konstante Beschleunigung mit additiven Prozessfehlern
- **Messmodelle:** Individuelle Beobachtungsgleichungen pro Sensormodalität
- **Latenzbehandlung:** Zeitstempel-Synchronisation und Verzögerungskompensation

---

## 3. Informationsverarbeitungspfade

### 3.1 Balisen-basierte Lokalisierung

#### 3.1.1 Funktionale Beschreibung

Das Balisensystem (BRV4) stellt absolute Positionsreferenzen über elektromagnetische Kopplung bereit. Der Verarbeitungspfad umfasst:

1. **Signaldetektion:** Fahrzeugantenne detektiert Balisensignal beim Überfahren
2. **Telegramm-Dekodierung:** Extraktion der Balisen-ID und Zusatzdaten
3. **Zeitstempel-Erfassung:** Präzise Zeitmessung des Detektionsereignisses
4. **Kartenabgleich:** Zuordnung Balisen-ID → Karten-Referenzposition
5. **Latenzkorrektur:** Kompensation von Verarbeitungs- und Kommunikationsverzögerungen

#### 3.1.2 Mathematisches Fehlermodell

Die Balisen-Positionsschätzung wird durch folgende Fehlerkomponenten beeinflusst:

**Longitudinaler Positionsfehler:**

```text
ε_balise_längs = v_fzg · t_latenz + ε_antenne_längs + ε_signal + ε_karte_längs

Wobei:
- v_fzg: Fahrzeuggeschwindigkeit [m/s]
- t_latenz ~ N(10ms, 2ms) trunc[6ms,14ms]: Verarbeitungslatenz
- ε_antenne_längs ~ N(0, 0.02m): Antennenpositionsoffset
- ε_signal: Signalqualitäts- und Umgebungseffekte (siehe Tabelle 4.1)
- ε_karte_längs ~ N(0, 0.019m): Kartenreferenzfehler
```

**Lateraler Positionsfehler:**

```text
ε_balise_quer = ε_antenne_quer + ε_signal_quer + ε_karte_quer

Mit vereinfachtem Signalmodell (ohne Latenzterm):
- ε_antenne_quer ~ N(0, 0.02m)
- ε_signal_quer: Reduzierte Signaleffekte
- ε_karte_quer ~ N(0, 0.014m)
```

#### 3.1.3 Ausfallmodellierung

Balisen-Ausfälle werden über ein Zwei-Zustand Markov-Modell beschrieben:

- **OK-Zustand:** p_detect = 0.99995 (sporadische Ausfälle p_miss = 5×10⁻⁵)
- **DEGRADED-Zustand:** p_detect = 0.95 (systematische Störungen)
- **Übergangswahrscheinlichkeiten:** p(OK→DEG) = 10⁻⁶, p(DEG→OK) = 0.01

### 3.2 Odometrische Positionsbestimmung

#### 3.2.1 Funktionale Beschreibung

Das Odometriesystem ermittelt relative Positionsänderungen über Radimpulszählung:

1. **Impulszählung:** Encoder erfasst Radumrandungen (typisch 100 Impulse/Umdrehung)
2. **Quantisierung:** Diskretisierung auf Impulsbasis (Δs ≈ 13.4mm bei 1.34m Radumfang)
3. **Skalierungskorrektur:** Adaptive Umfangsanpassung basierend auf Balisenabständen
4. **Integration:** Kumulation der Wegstrecke zwischen Balisen-Ankern
5. **Rückstellung:** Nullstellung des akkumulierten Fehlers bei jeder Balisen-Detektion

#### 3.2.2 Mathematisches Fehlermodell

**Segmentfehler zwischen Balisen:**

```text
ε_odo_segment = Σ(ε_quant_i) + ε_drift_segment + ε_umfang_residual

Komponenten:
- ε_quant_i ~ U(-Δs/2, Δs/2): Quantisierungsfehler pro Increment
- ε_drift_segment ~ N(0, (0.010 m/km)·d_segment): Sistematischer Drift
- ε_umfang_residual ~ U(-0.03m, 0.03m): Verbleibender Umfangsfehler nach Kalibrierung
```

**RMS-Fehler für 1km Segment:**
- Quantisierung: ~4.5mm (dominante Varianzquelle ~65%)
- Drift: ~10mm vor Kalibrierung
- Residual-Umfang: ~17mm (±30mm Bereich)

**Zeitliche Fehlerentwicklung:**
Der Odometriefehler wächst kontinuierlich zwischen Balisen und wird bei jeder Balisen-Detektion zurückgesetzt, wodurch unbegrenzte Fehlerakkumulation verhindert wird.

### 3.3 Digitale Karten-Referenzierung

#### 3.3.1 Funktionale Beschreibung

Die digitale Karte stellt die geometrische Reference für alle Lokalisierungskomponenten bereit:

1. **Gleisgeometrie:** Präzise 3D-Modellierung der Schienenverläufe
2. **Referenzpunkte:** Definierte Koordinaten für Balisen und kritische Infrastruktur
3. **Interpolation:** Berechnung von Zwischenpositionen zwischen Stützpunkten
4. **Projektion:** Abbildung aller Sensormessungen auf das Gleiskoordinatensystem

#### 3.3.2 Mathematisches Fehlermodell

**Geometrische Basisfehler:**
```
ε_karte_basis_längs ~ N(0, 0.020m): Vermessungsungenauigkeit Gleisachse
ε_karte_basis_quer ~ N(0, 0.015m): Kombinierter Höhen-/Querversatz
```

**Interpolationsfehler:**
```
ε_interpolation ~ Exp(λ=0.02) trunc[0, 0.05m]: Fehler zwischen Stützpunkten
Gewichtung: w_interp = 0.3 (30% Anteil am Gesamtfehler)
```

**Skalierungsfehler:**
```
ε_skalierung = α_skala · d_strecke
α_skala ~ N(0, 6×10⁻⁴): Proportionaler Skalierungsfehler (0.06%)
Relevanz: Nur bei Strecken > 2km signifikant
```

**Räumliche Korrelation:**
Kartenfehler weisen exponentielle Korrelation auf: Cov(ε₁,ε₂) = σ²·exp(-|r₁-r₂|/r₀) mit r₀ = 75m

### 3.4 GNSS-gestützte Positionierung

#### 3.4.1 Funktionale Beschreibung

Das GNSS-System liefert absolute Positionsinformation mit umgebungsabhängiger Verfügbarkeit und Genauigkeit:

1. **Signalempfang:** Multi-Satelliten-Signalverarbeitung
2. **Positionsberechnung:** Trilateration mit Uhrenkorrektur
3. **Qualitätsbewertung:** DOP-Analyse und Signalstärkeüberwachung
4. **Projektions:** Transformation in Gleiskoordinatensystem

#### 3.4.2 Umgebungsabhängige Fehlermodelle

| Umgebung | Bias σ_bias [m] | Messrauschen σ_noise [m] | Ausfallrate p_outage | Multipath-Zusatz |
|----------|-----------------|--------------------------|---------------------|-------------------|
| **Open** | 0.25 | 0.30 | 0.01 | — |
| **Urban** | 0.50 | 0.80 | 0.05 | Exp(λ=2, cap=3m, w=0.1) |
| **Tunnel** | n/a | n/a | 1.0 | — |

### 3.5 IMU-basierte Trägheitsnavigation

#### 3.5.1 Funktionale Beschreibung

Das IMU-System stellt hochfrequente Bewegungsinformation zur Überbrückung von Sensorausfällen bereit:

1. **Beschleunigungsmessung:** 3-Achsen Accelerometer
2. **Drehratenmessung:** 3-Achsen Gyroskop  
3. **Strapdown-Integration:** Numerische Integration zu Geschwindigkeit und Position
4. **Bias-Korrektur:** Adaptive Schätzung und Kompensation von Sensorfehlern

#### 3.5.2 Mathematisches Fehlermodell

**Accelerometer-Modell:**
```
a_mess = a_wahr + b_accel + n_accel + w_accel

b_accel ~ N(0, 0.005 m/s²): Konstanter Bias
n_accel: Weißrauschen, PSD = 0.05 m/s²/√Hz
w_accel: Bias Random Walk, τ = 900s
```

**Gyroskop-Modell:**
```
ω_mess = ω_wahr + b_gyro + n_gyro + w_gyro

b_gyro ~ N(0, 0.02 °/s): Konstanter Bias
n_gyro: Weißrauschen, PSD = 0.01 °/s/√Hz
w_gyro: Bias Random Walk, τ = 900s
```

---

## 4. Fehlermodellierung und -quantifizierung

### 4.1 Systematische Fehleridentifikation

Die Fehlerquellen werden nach folgender Systematik klassifiziert und priorisiert:

**Klassifikation nach Wirkungsgrad:**
- **HOCH:** Dominante Beiträge zur Gesamtvarianz (>10% Varianzanteil)
- **MITTEL:** Signifikante Beiträge (1-10% Varianzanteil)  
- **NIEDRIG:** Minimale Beiträge (<1% Varianzanteil, aber sicherheitsrelevant)

**Klassifikation nach Zeitverhalten:**
- **Systematisch:** Konstante oder langsam veränderliche Offsets
- **Zufällig:** Weißes oder korreliertes Rauschen
- **Episodisch:** Seltene, aber signifikante Ereignisse (Ausfälle, Störungen)

### 4.2 Konsolidierte Fehlerparametertabelle

| Fehlerquelle | Longitudinal | Lateral | Zeitverhalten | Modell | Parameter | Relevanz | Bemerkung |
|--------------|-------------|---------|---------------|---------|-----------|----------|-----------|
| **Balisen** | | | | | | | |
| Latenz | v·t_latenz | — | Systematisch | N(10ms,2ms) trunc[6,14]ms | μ=10ms, σ=2ms | HOCH | Geschwindigkeitsabhängig |
| Antennenoffset | N(0,σ) | N(0,σ) | Systematisch | Normal | σ=0.02m | MITTEL | Montageungenauigkeit |
| EM-Störung | Rayleigh | Rayleigh | Zufällig | Rayleigh | σ=0.012m | NIEDRIG | Umgebungsabhängig |
| Multipath | Exp trunc | — | Episodisch | Exp(λ=0.05) cap 0.08m | w=0.15 | MITTEL | Heavy-tail Komponente |
| Witterung | Uniform | Uniform | Zufällig | Uniform | ±0.015m | NIEDRIG | Temperatur/Feuchte |
| Ausfall | — | — | Episodisch | Markov | p_miss≈1×10⁻⁴ | MITTEL | Sicherheitsrelevant |
| **Odometrie** | | | | | | | |
| Quantisierung | Uniform | — | Deterministisch | Uniform | ±6.7mm (Δs/2) | MITTEL | Encoder-Auflösung |
| Drift | Normal | — | Systematisch | N(0,σ_drift·d) | σ_drift=0.01m/km | MITTEL | Kalibrierungsfehler |
| Umfang residual | Uniform | — | Systematisch | Uniform | ±0.03m (±0.10m Stress) | MITTEL | Nach Korrektur |
| **Digitale Karte** | | | | | | | |
| Geometrie basis | N(0,σ) | N(0,σ) | Systematisch | Normal | σ_längs=0.019m, σ_quer=0.014m | MITTEL | Vermessungsgenauigkeit |
| Interpolation | Exp trunc | — | Systematisch | Exp(λ=0.02) cap 0.05m | w=0.3 | NIEDRIG | Zwischen Stützpunkten |
| Skalierung | α·d | — | Systematisch | N(0,6×10⁻⁴)·d | nur für d>2km | NIEDRIG | Proportional |
| **GNSS** | | | | | | | |
| Bias (Open) | N(0,σ) | N(0,σ) | Systematisch | Normal | σ=0.25m | HOCH | Atmosphäre/Uhr |
| Noise (Open) | N(0,σ) | N(0,σ) | Zufällig | Normal | σ=0.30m | HOCH | Empfängerfehler |
| Bias (Urban) | N(0,σ) | N(0,σ) | Systematisch | Normal | σ=0.50m | HOCH | Multipath verstärkt |
| Noise (Urban) | N(0,σ) | N(0,σ) | Zufällig | Normal | σ=0.80m | HOCH | Signaldegradation |
| Multipath (Urban) | Exp trunc | Exp trunc | Episodisch | Exp(λ=2) cap 3m | w=0.1 | MITTEL | Heavy-tail |
| Outage | — | — | Episodisch | Bernoulli | p_open=0.01, p_urban=0.05 | HOCH | Verfügbarkeit |
| **IMU** | | | | | | | |
| Accel Bias | Integration | Integration | Systematisch | N(0,0.005m/s²) + RW | τ=900s | MITTEL | Temperaturabhängig |
| Gyro Bias | Integration | Integration | Systematisch | N(0,0.02°/s) + RW | τ=900s | MITTEL | Langzeitdrift |
| Accel Noise | Integration | Integration | Zufällig | Weißrauschen | 0.05 m/s²/√Hz | NIEDRIG | Hochfrequent |
| Gyro Noise | Integration | Integration | Zufällig | Weißrauschen | 0.01 °/s/√Hz | NIEDRIG | Hochfrequent |
| **Fusion** | | | | | | | |
| Latenz | v·Δt | — | Systematisch | N(20ms,5ms) trunc[10,35]ms | Gain-reduziert | MITTEL | Verarbeitungszeit |
| Jitter | — | — | Zufällig | In Latenz absorbiert | — | NIEDRIG | Zeitstempel |

### 4.3 Korrelationen zwischen Fehlerquellen

Die Korrelationsstruktur berücksichtigt gemeinsame Referenzen und physikalische Kopplungen:

| Korrelationspaar | ρ | Begründung |
|------------------|---|------------|
| Karte ↔ GNSS | 0.80 | Gemeinsame Projektions- und Map-Matching-Referenz |
| Karte ↔ Balise | 0.65 | Balisen-Referenzpositionen aus Kartendatenbasis |
| Balise ↔ Odometrie | 0.80 | Odometrie-Nullstellung bei Balisen-Events |
| Odometrie ↔ GNSS | 0.25 | Schwache Kopplung über Bewegungsdynamik |
| GNSS ↔ Balise | 0.30 | Gemeinsame Kartenoffsets |
| IMU ↔ Odometrie | 0.40 | Gemeinsame Fahrzeugdynamik |
| IMU ↔ GNSS | 0.20 | Bewegungsdynamik, verschiedene Fehlerarten |

**Validierungskriterium:** |ρ_sample - ρ_target| ≤ 0.05

### 4.4 Zeitabhängige Fehlerfortpflanzung

**Kurzzeit-Dynamik (< 1 Sekunde):**
- GNSS/IMU: Hochfrequente Messungen mit Rauschkorrelation
- Balise: Ereignis-getriggerte Korrekturen
- Odometrie: Kontinuierliche Integration mit Quantisierungsrauschen

**Mittelzeit-Dynamik (1 Sekunde - 1 Minute):**
- IMU-Bias-Drift wird dominant
- GNSS-Ausfälle in Urban/Tunnel-Umgebung
- Odometrie-Drift zwischen Balisen akkumuliert

**Langzeit-Dynamik (> 1 Minute):**
- Balisen-Reset verhindert unbegrenzte Fehlerakkumulation
- GNSS-Bias-Variation über Satellitenkonstellation
- Temperaturbedingte Sensorparameter-Drift

---

## 5. Unterscheidung: Sicherer und unsicherer Lokalisierungspfad

### 5.1 Sicherer Pfad (SIL1-relevant)

**Architekturprinzip:**
Der sichere Pfad implementiert das Fail-Safe-Prinzip durch redundante, unabhängige Sensoren mit deterministischen Ausfallmodi.

**Komponenten:**
- **Balisen:** Passive Transponder mit elektromagnetischer Kopplung
- **Odometrie:** Mechanische Wegmessung an nicht-angetriebener Achse  
- **Digitale Karte:** Statische Referenzdatenbank

**Fehlercharakteristika sicherer Pfad:**
- Deterministische oder gut charakterisierte stochastische Fehler
- Begrenzte Fehlerakkumulation durch periodische Referenzierung
- Ausfälle erkennbar und handhabbar
- Konservative Fehlermodellierung

**Typische Fehlergrößen (95%-Perzentil):**
- Balise longitudinal: ~18cm (inkl. Latenz bei 60 km/h)
- Odometrie pro Segment: ~13cm RMS
- Karte Referenz: ~4cm (geometrische Basis)

### 5.2 Unsicherer Pfad (Präzisionserweiterung)

**Architekturprinzip:**
Der unsichere Pfad zielt auf höchste Präzision unter optimalen Bedingungen, mit Degradation bei ungünstigen Umgebungen.

**Komponenten:**
- **GNSS:** Satellitennavigation mit Umgebungsabhängigkeit
- **IMU:** Trägheitssensoren für hochfrequente Bewegungsschätzung
- **Fusion-Algorithmus:** Probabilistische Sensorkombination

**Fehlercharakteristika unsicherer Pfad:**
- Stark umgebungsabhängige Fehlerverteilungen
- Potentielle Heavy-Tail-Verteilungen (Multipath, Interferenz)
- Unvorhersagbare Ausfallmuster
- Optimistische Fehlermodellierung möglich

**Typische Fehlergrößen (95%-Perzentil):**
- GNSS Open: ~1.2m (kombiniert Bias+Noise)
- GNSS Urban: ~3.2m (mit Multipath-Tail)
- IMU (20s Integration): ~5-50cm je nach Trajectory

### 5.3 Fehlerfortpflanzung im Gesamtsystem

**Fusionsstrategie:**
Die Kombination beider Pfade erfolgt über gewichtete Mittelung mit varianz-inversen Gewichten:

```
w_sicher = σ²_unsicher / (σ²_sicher + σ²_unsicher)
w_unsicher = σ²_sicher / (σ²_sicher + σ²_unsicher)

x_fused = w_sicher · x_sicher + w_unsicher · x_unsicher
σ²_fused = (σ²_sicher · σ²_unsicher) / (σ²_sicher + σ²_unsicher)
```

**Betriebsmodi:**
1. **Normal:** Beide Pfade verfügbar → optimale Präzision
2. **GNSS-Degraded:** Urban/Tunnel → sicherer Pfad dominant
3. **Balise-Sparse:** Große Balisenabstände → unsicherer Pfad überbrückt
4. **Backup:** Nur sicherer Pfad → garantierte Mindestgenauigkeit

**Kritische Übergangsszenarien:**
- Open→Tunnel Transition: GNSS-Ausfall erfordert IMU-Überbrückung
- Balise-Ausfall bei gleichzeitigem GNSS-Problem: Reine Odometrie-Navigation
- Urban Heavy Multipath: Temporäre Verschlechterung beider Pfade

---

## 6. Methodische Umsetzung und nächste Schritte

### 6.1 Monte-Carlo-Simulationsansatz

**Simulationsparameter:**
- Stichprobengröße: N = 10.000 Runs (Stabilität P99-Schätzung)
- Zeithorizont: 3600s (1 Stunde kontinuierlicher Betrieb)
- Zeitschrittweite: dt = 0.1s (ausreichend für 60 km/h Dynamik)
- Bootstrap-Samples: B = 500 (Konfidenzintervall-Schätzung)

**Validierungsstrategie:**
- Korrelationsvalidierung: Sample-Korrelationen vs. Zielwerte (Toleranz ±0.05)
- Plausibilitätschecks: Monotonie-Tests für Parameter-Sensitivity
- Referenzvalidierung: Vergleich mit verfügbaren Realdatensätzen (falls vorhanden)

### 6.2 Erwartete Zielmetriken

**Primäre Kennzahlen:**
- RMSE longitudinal < 0.20m (Zielanforderung)
- Perzentile: P50, P90, P95, P99 (longitudinal/lateral/2D)
- Verfügbarkeit: Anteil verfügbarer Positionsschätzungen
- Konfidenzintervalle: Bootstrap-basierte 95%-CIs

**Sensitivitätsanalyse:**
- One-at-a-Time (OAT): ±10% Variation aller Modellparameter
- Ranking: Relative RMSE-Änderung pro Parametervariante
- Optional: Sobol-Indizes für Haupteffekte und Wechselwirkungen

### 6.3 Implementierung und Reproduzierbarkeit

**Software-Architektur:**
- Python 3.11 mit numpy/scipy/pandas/matplotlib
- Modulare Struktur: config.py, sensors.py, fusion.py, metrics.py
- CLI-Interface: `python run_sim.py --config model.yml --output results/`

**Konfigurationsmanagement:**
- YAML-basierte Parametrierung mit Versionierung
- Seed-basierte Reproduzierbarkeit
- Automatisierte Test-Suite für Regressionsschutz

### 6.4 Erwarteter Berichtumfang

**Finale Deliverables:**
- Methodenbericht (10-15 Seiten) mit vollständiger Dokumentation
- Kennzahlen-Tabellen mit Konfidenzintervallen
- Visualisierungen: PDF/CDF, Zeitreihen, Sensitivitäts-Rankings
- Konfigurationsdateien und reproduzierbarer Quellcode
- Executive Summary für Management-Ebene

---

## 7. Stakeholder-Feedback und Freigabe

**Erforderliche Bestätigungen:**
1. Vollständigkeit der berücksichtigten Fehlerquellen
2. Plausibilität der Fehlerparameter und -modelle  
3. Angemessenheit der Korrelationsannahmen
4. Akzeptanz der Simulationsparameter (N, dt, Zeithorizont)
5. Zustimmung zu den Zielmetriken und Bewertungskriterien

---

*Dieser Bericht dient der methodischen Abstimmung und enthält keine Vorabergebnisse. Die quantitative Analyse erfolgt nach Freigabe der Parameter und Modelle durch die Stakeholder.*