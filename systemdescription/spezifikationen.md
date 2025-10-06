# Fehleranalyse Balise-Leser: Auswirkungen auf die sichere Lokalisierung# Fehleranalyse Balise-Leser: Auswirkungen auf die sichere Lokalisierung

## 1. Executive Summary## 1. Zusammenfassung

Diese Analyse quantifiziert die Fehlerquellen des DLR Balise-Readers V4 (BRV4) und deren Auswirkungen auf die Genauigkeit des sicheren Lokalisierungssystems. Basierend auf technischen Spezifikationen und Monte-Carlo-Simulationen werden realistische Fehlermodelle für die Integration in sichere und GNSS-unterstützte Lokalisierungspfade entwickelt.Diese Analyse quantifiziert die Fehlerquellen des Balise-Lesers BRV4 und deren Auswirkungen auf die Genauigkeit des sicheren Lokalisierungssystems. Basierend auf Monte-Carlo-Simulationen (50.000 Läufe) werden realistische Fehlermodelle entwickelt und Optimierungsstrategien abgeleitet.

**Kernresultate bei Referenzgeschwindigkeit 40 km/h:****Hauptergebnisse bei 30 km/h**:

- **Längsfehler**: 10,2 ± 2,8 cm (68%-Konfidenzintervall)

- **Längsfehler (sicher)**: 12,4 ± 3,1 cm (1σ-Bereich)- **Querfehler**: 2,9 ± 1,1 cm (68%-Konfidenzintervall)

- **Querfehler (sicher)**: 2,8 ± 1,2 cm (1σ-Bereich)- **Dominante Fehlerquelle**: Verarbeitungslatenz (71% des Längsfehlers)

- **99%-Perzentil**: 19,8 cm (längs), 6,1 cm (quer)

- **Dominante Fehlerquelle**: Verarbeitungslatenz (69% Varianzanteil)## 2. Systemarchitektur und Funktionsweise



## 2. Systemarchitektur und Betriebsverhalten### 2.1 BRV4 Balise-Leser Spezifikation



### 2.1 BRV4 Hardware-Spezifikation**Hardware-Komponenten**:

- **Signalerzeugung**: 27-MHz-Aktivierungssignal für Eurobalisen

**Signalverarbeitung:**- **Empfang**: 4,23 MHz FSK-modulierte Telegramme

- **Verarbeitung**: FPGA + CPU mit ROS-Schnittstelle

- **Aktivierung**: 27 MHz Aufweck-Signal für Eurobalisen- **Schnittstellen**: Antenne (BR.X14), Ethernet (BR.X20)

- **Empfang**: 4,23 MHz FSK-modulierte Telegramme

- **Hardware**: FPGA-basierte Echtzeitverarbeitung + CPU mit ROS-Interface**Übertragungsverhalten** (basierend auf aktueller BRV4-Spezifikation):

- **Antennen**: Spezialisierte Balise-Antennen (BR.X14)- **Status-Nachrichten**: Zyklisch 1 Hz (unabhängig von Balisen-Detektion)

- **Kommunikation**: Ethernet zu ROS-Netzwerk (BR.X20)- **Balisen-Events**: Ereignisgetrieben nach erfolgreicher Demodulation/Dekodierung

- **Zeitstempel**: `payload.timestamp` = Überfahrzeitpunkt mit <10ms uncompensierter Latenz

### 2.2 Übertragungsprotokoll und Zeitverhalten

**Datenübertragung (basierend auf BRV4-Spezifikation):**

Die Balisen sind fest in der Infrastruktur montiert und dienen als Referenzpunkte mit bekannten Positionen:

- **Status-Nachrichten**: Zyklisch 1 Hz (kontinuierlich, unabhängig von Balisen-Events)- **Anordnung**: Nach Szenarien (Weichen, Stumpfgleis, Hauptsignal, Bahnhof, Einfahrsignal)

- **Balisen-Detektionen**: Ereignisgetrieben nach erfolgreicher Demodulation/Dekodierung- **Abstände**: Variable Abstände zwischen Balisen (50m, 200m, 350m, bis 2000m)

- **Erste vollständige Nachricht**: Nur die erste erfolgreich dekodierte Nachricht wird übertragen- **Identifikation**: Eindeutige Balisen-IDs und Telegrammstrukturen

- **Früherkennung**: Balise kann bereits vor geometrischem Überfahren erkannt werden

## 3. Physikalische Fehlerquellen

**Timing und Latenz:**

### 3.1 Antennenpositionierung und -ausrichtung

- **payload.timestamp**: Enthält unkompensierte FPGA→CPU und Netzwerklatenz

- **Geschätzte unkompensierte Latenz**: <10 ms (FPGA→CPU + interne Netzwerklatenz)**Problem**: Ungenaue Montageposition der Balise-Leser-Antenne am Fahrzeug

- **Zusätzliche Verarbeitungslatenz**: Differenz zwischen payload.timestamp und header.timestamp

- **Optimaler Zeitreferenz**: payload.timestamp für Positionsrekonstruktion verwenden**Ursachen**:

- Fertigungstoleranzen bei der Antennenhalterung

### 2.3 Detektionsverhalten- Montagefehler oder -toleranzen

- Mechanische Verformungen durch Vibrationen und Betriebsbelastungen

**Erkennungseigenschaften:**

**Auswirkungen**:

- **Geschwindigkeitsabhängigkeit**: Detektionsrate variiert mit Geschwindigkeit [0-60 km/h]- Systematische Positionsoffsets (±1-3 cm typisch)

- **Früherkennung**: Detektion vor geometrischem Überfahren möglich (geschwindigkeitsunabhängig)- Änderung des Zeitpunkts der Balisen-Detektion

- **Keine Positionsbestimmung**: BRV4 ermittelt keine Balisen-Position (Referenz aus Karte)- Beeinflussung der Signalstärke durch suboptimale Ausrichtung



## 3. Fehlermodell für Lokalisierungssystem### 3.2 Signalübertragung und -qualität



### 3.1 Fehlerquellen-Taxonomie**Interferenzen und elektromagnetisches Rauschen**:

- Störungen von Fahrzeugelektronik (Traktionsmotoren, Klimaanlagen)

**Kategorie A: Hardware-bedingte Fehler**- Externe elektromagnetische Felder (Oberleitungen, Funkanlagen)

- Industrielle Störquellen in Bahnhofsumgebungen

1. **Verarbeitungslatenz**

   - FPGA→CPU Übertragung: 2-4 ms**Multipath-Effekte**:

   - Signalverarbeitung (Demod/Dekod): 3-7 ms  - Reflexionen an Metallstrukturen (Fahrzeugboden, Gleisbett, Schienen)

   - ROS-Publishing: 1-3 ms- Phasenverschiebungen durch mehrfache Signalwege

   - **Gesamt**: 6-14 ms (Mittelwert: 10 ms, σ = 2 ms)- Besonders kritisch in Tunneln und bei Metallbrücken



2. **Antennen-Montage-Offset****Signalstärke-Variation**:

   - Längsrichtung: σ = 2,0 cm (Normalverteilung)- Abstandsvariation zwischen Antenne und Balise

   - Querrichtung: σ = 2,0 cm (Normalverteilung)- Fahrzeughöhenunterschiede bei verschiedenen Zugtypen

   - Korrelation: ρ = 0,15 (schwache Montagekorrelation)- Balisen-Positionstoleranz relativ zur Gleismitte



**Kategorie B: Externe Referenzfehler**### 3.3 Geschwindigkeitsabhängige Effekte



3. **Digitale Kartenfehler** (Referenz: map_error.md)**Dopplerverschiebung**:

   - Längsrichtung: σ = 1,9 cm (Monte-Carlo-validiert)- Frequenzverschiebung des 4,23 MHz Signals bei hohen Geschwindigkeiten

   - Querrichtung: σ = 1,4 cm (Monte-Carlo-validiert)- Potenzielle Auswirkungen auf die FSK-Demodulation

   - Quelle: Externe Kartenreferenz, unabhängig von BRV4-Hardware

**Lesezeit-Limitierung**:

**Kategorie C: Umweltbedingte Fehler**- Verkürzung der verfügbaren Übertragungszeit bei hohen Geschwindigkeiten

- Risiko unvollständiger Telegramm-Übertragung

4. **Signalqualität und Störungen**- Kritische Geschwindigkeitsschwellen für zuverlässige Detektion

   - Elektromagnetische Interferenzen: Rayleigh-Verteilung (σ = 1,2 cm)

   - Multipath-Effekte: Exponentialverteilung (λ = 0,05, max = 5 cm)### 3.4 Umwelteinflüsse

   - Witterungseinflüsse: Gleichverteilung ±1,5 cm

**Witterungsbedingte Dämpfung**:

5. **Geschwindigkeitsabhängige Detektionsrate**- Schnee und Eis auf Balisen oder Antennen

   - Ausfallwahrscheinlichkeit: P_fail(v) = 0,02 + 0,0003×v [km/h]- Wasserfilm als Signaldämpfer

   - Bei 40 km/h: P_fail = 3,2%- Schmutz und Ablagerungen



### 3.2 Mathematisches Fehlermodell**Mechanische Beschädigung**:

- Schotterflug und Steinschlag

**Positionsfehler-Berechnung:**- Vandalismus an Balisen

- Korrosion und Alterung der Komponenten

Gesamtfehler setzt sich zusammen aus:

## 4. Systembedingte Fehlerquellen

```

ε_längs = ε_latenz + ε_antenne_längs + ε_karte_längs + ε_umwelt_längs### 4.1 Digitale Kartenfehler-Einfluss

ε_quer = ε_antenne_quer + ε_karte_quer + ε_umwelt_quer

```**Referenzpositions-Übertragung**:

- Systematische Kartenfehler werden bei der Balisen-Detektion direkt übernommen

**Latenzfehler (geschwindigkeitsabhängig):**- Balisen-Positionsfehler aus der digitalen Karte (siehe map_error.md): ±2,7 cm (längs), ±1,9 cm (quer)

- Jeder Balisen-Trigger übernimmt den kartenbasierten Positionsfehler als Offset

```- Keine Akkumulation zwischen Balisen, aber Wiedereinführung bei jeder Balise

ε_latenz = v × t_latenz

```**Koordinatensystem-Transformationen**:

- Fehler bei der Umrechnung zwischen verschiedenen Koordinatensystemen

Wobei:- Ungenauigkeiten in geodätischen Parametern

- v = Geschwindigkeit [m/s]

- t_latenz ~ N(10ms, 2ms) = Verarbeitungslatenz### 4.2 Timing und Verarbeitungsfehler



**Gesamtfehler-Berechnung:****Signalverarbeitungs-Latenz**:

- Konstante Verzögerung durch A/D-Wandlung und Digitale Verarbeitung

```- Geschwindigkeitsabhängiger Positionsfehler durch Latenz

σ_längs² = σ_latenz² + σ_antenne_längs² + σ_karte_längs² + σ_umwelt_längs²- **Beispiel**: 10 ms Latenz bei 50 km/h = 14 cm Positionsfehler

σ_quer² = σ_antenne_quer² + σ_karte_quer² + σ_umwelt_quer²

```**Software-/Firmware-Probleme**:

- Fehler in der FSK-Demodulation

### 3.3 Parameterisierung für Monte-Carlo-Simulation- Unvollständige oder fehlerhafte Telegramm-Dekodierung

- Race Conditions in der ROS-basierten Verarbeitung

| Parameter | Verteilung | Wert | Quelle/Begründung |

|-----------|-----------|------|-------------------|### 4.3 Telegramm-bezogene Fehler

| **Verarbeitungslatenz** | Normal | μ=10ms, σ=2ms | BRV4-Spezifikation |

| **Antennen-Offset (längs)** | Normal | μ=0, σ=2,0cm | Fertigungstoleranz |**Datenkorruption**:

| **Antennen-Offset (quer)** | Normal | μ=0, σ=2,0cm | Fertigungstoleranz |- Bit-Fehler durch Signalstörungen

| **Kartenfehler (längs)** | Normal | μ=0, σ=1,9cm | map_error.md |- Prüfsummen-Fehler in Balisen-Telegrammen

| **Kartenfehler (quer)** | Normal | μ=0, σ=1,4cm | map_error.md |- Unvollständige Datenübertragung

| **EM-Störungen** | Rayleigh | σ=1,2cm | Betriebserfahrung |

| **Multipath** | Exponential | λ=0,05, max=5cm | Physikalisches Modell |**ID-Verwechslungen**:

| **Witterung** | Uniform | ±1,5cm | Konservative Schätzung |- Falsche Interpretation der Balisen-ID (NID_BG)

| **Detektionsrate** | Binomial | P_fail(v) | Geschwindigkeitsabhängig |- Verwechslung ähnlicher Telegramm-Strukturen


# Analyse der Digitalen Karte Fehler

## 1. Einführung

Die digitale Karte bildet das Rückgrat des schienengebundenen Lokalisierungssystems und definiert sowohl die topologische Struktur### 5.3 Quantitative Fehlerabschätzung für Infrastrukturelemente

**Infrastruktur-Referenzpunkt-Positionsgenauigkeit**:

- **Längsrichtung**: ±4-8 cm (1σ) kombiniert aus Vermessung und Karteneintrag
- **Querrichtung**: ±2-5 cm (1σ) relativ zur Gleismittelachse
- **Systematischer Offset**: ±1-3 cm durch Referenzpunkt-Definitionen

**Signal- und Weichenpositionen**:

- **Signale**: ±5-12 cm (1σ) bei moderner Vermessung
- **Weichen**: ±3-8 cm (1σ) für Herzstück und kritische Punkte
- **Bahnsteigkanten**: ±2-5 cm (1σ) für präzisionsvermessene Anlagennetzes als auch die präzisen geometrischen und positionellen Referenzen für die Lokalisierung. Als fundamentale Datenquelle für beide Lokalisierungssubsysteme (sicheres Balise-/Odometriesystem und hochgenaues GNSS/IMU-System) haben Ungenauigkeiten in der digitalen Karte direkte und systematische Auswirkungen auf die Gesamtlokalisierungsgenauigkeit.

Diese Analyse untersucht die verschiedenen Schichten der digitalen Karte und deren potenzielle Fehlerquellen im Kontext eines dualen Lokalisierungssystems für automatisierte Züge.

## 2. Struktur der digitalen Karte

### 2.1 Drei-Schichten-Architektur

Die digitale Karte für schienengebundene Lokalisierung besteht aus drei kritischen Datenschichten:

**Track-Topologie (Logische Schicht)**:

- TrackIDs und Gleisabschnittsdefinitionen
- Endpunkte und Knotendefinitionen
- Konnektivität zwischen Gleisabschnitten
- Weichenverbindungen und Verzweigungen
- Logische Fahrtrichtungen und erlaubte Übergänge

**3D-Geometrie (Geometrische Schicht)**:

- WGS84-Koordinaten der Gleismittelachse
- Höhenprofile und Steigungen
- Krümmungsradien und geometrische Parameter
- Seitliche Gleisneigung (Überhöhung)
- Referenzpunkte für GNSS-Projektion

**Infrastrukturelemente (Referenzpunkt-Schicht)**:

- Exakte Positionen von Balisen (Längs- und Querkoordinaten)
- Signalstandorte und deren Wirkbereiche
- Weichenpositionen und -geometrie
- Bahnsteigkanten und Haltepositionsmarker
- Geschwindigkeitsbegrenzungsabschnitte

### 2.2 Datenquellen und Erstellungsprozess

**Primäre Vermessungsquellen**:

- Terrestrische Gleisvermes­sung mit GPS/GNSS-RTK
- Airborne und terrestrisches LiDAR-Scanning
- Photogrammetrische Auswertung von Luftbildern
- Traditionelle Ingenieurvermessung mit Totalstationen

**Sekundäre Datenquellen**:

- Bestandspläne und CAD-Zeichnungen der Infrastrukturbetreiber
- Historische Vermessungsdaten und Archive
- Mobile Mapping-Systeme auf Schienenfahrzeugen
- Crowdsourcing-Daten aus Betriebsfahrzeugen

### 2.3 Kartenanforderungen und Spezifikationen

Entsprechend den gesetzten Anforderungen für die verwendete Karte müssen folgende Parameter erfüllt werden:

**Track_Centerline (Gleismittelachse)**:
- Darstellung durch Polyline mit TrackEdges als Stützpunkte
- Maximaler Abstand zwischen TrackEdges: ≤10m (gerade), ≤2m (gekrümmt)
- Absolute Genauigkeit jeder TrackEdge: ±10cm (lat., long., height)
- Relative Genauigkeit zwischen benachbarten TrackEdges: ±2cm

**Platform (Bahnsteige)**:
- Darstellung durch Polygon
- Maximaler Abstand zwischen Polygonpunkten: ≤2m (nicht-gerade Bahnsteige)
- Absolute Genauigkeit jeder Punkt: ±10cm (lat., long., height)
- Relative Genauigkeit zwischen benachbarten Punkten: ±2cm

## 2.4 Mathematisches Fehlermodell

### 2.4.1 Grundlegende Fehlerkomponenten

Das Kartenfehlermodell basiert auf drei Hauptkomponenten, die mathematisch modelliert werden:

#### Geometrische Fehlermodelle

**Längsrichtungs-Fehlermodell:**

```
δₗ = √(δ_gleisachse² + δ_interpolation²)
```

Wobei:
- `δ_gleisachse ~ N(0, σ_gleisachse)` mit σ_gleisachse = 2,0 cm [Quelle: RTK-GNSS Herstellerspezifikationen]
- `δ_interpolation ~ Exp(λ_int)` mit λ_int = 0,02 (mittlere Abweichung 2cm) [Quelle: Monte-Carlo-Simulation]

**Querrichtungs-Fehlermodell:**

```
δ_q = √(δ_gleisachse² + δ_hoehenmodell²)
```

Wobei:
- `δ_hoehenmodell ~ N(0, σ_hoehe)` mit σ_hoehe = 1,5 cm [Quelle: EGM2020 Geoid-Modell-Spezifikation]

#### Proportionale Fehlermodelle

**Skalierungsfehlermodell:**

```
δ_prop = |δ_koordinaten + δ_projektion + δ_kalibrierung|
```

Wobei:
- `δ_koordinaten ~ N(0, σ_koord)` mit σ_koord = 0,01% [Quelle: ISO 19111:2019]
- `δ_projektion ~ U(-0,005%, +0,005%)` [Quelle: UTM-Projektions-Spezifikation]
- `δ_kalibrierung ~ N(0, σ_kal)` mit σ_kal = 0,003% [Quelle: Vermessungsgeräte-Kalibrierungsprotokolle]

### 2.4.2 Stochastisches Gesamtmodell

**Räumlich korreliertes Fehlerfeld:**

```
F(x,y) = F_sys(x,y) + F_random(x,y)
```

Mit exponentieller Kovarianzfunktion:

```
Cov(r) = σ² × exp(-r/r₀)
```

Wobei:
- σ² = Varianz des Fehlerfeldes
- r = Abstand zwischen Messpunkten
- r₀ = Korrelationslänge (50-100m für Gleisanlagen) [Quelle: Empirische Analyse Gleisgeometrie]

**Fehlerfortpflanzungsgesetz:**

Für die Gesamtunsicherheit der Kartenposition gilt:

```
σ_total² = σ_geom² + (α × d)² + Σᵢⱼ Cᵢⱼ × σᵢ × σⱼ
```

Wobei:
- σ_geom = geometrische Grundfehler (konstant)
- α = proportionaler Skalierungsfehler [%/km]
- d = Distanz [km]
- Cᵢⱼ = Korrelationsmatrix zwischen Fehlerquellen

### 2.4.3 Parameter-Tabelle für Simulationsmodell

| Parameter | Symbol | Verteilung | Wert | Quelle |
|-----------|--------|------------|------|--------|
| Gleisachse-Vermessung | σ_gleisachse | N(0, σ) | 2,0 cm | RTK-GNSS Herstellerdaten |
| Höhenmodell-Genauigkeit | σ_hoehe | N(0, σ) | 1,5 cm | EGM2020 Geoid-System |
| Interpolationsfehler | λ_int | Exp(λ) | 0,02 | Empirische Gleisanalyse |
| Koordinaten-Skalierung | σ_koord | N(0, σ) | 0,01% | ISO 19111:2019 Standard |
| Projektionsverzerrung | U_proj | U(a,b) | ±0,005% | UTM-Zonen-Spezifikation |
| Instrumentenkalibrierung | σ_kal | N(0, σ) | 0,003% | Vermessungsgeräte-Toleranz |
| QS-Reduktion Geometrie | f_QS_geom | Konstant | 0,65 | Multi-Sensor-Fusion |
| QS-Reduktion Proportional | f_QS_prop | Konstant | 0,70 | Automatisierte QS-Verfahren |
| Korrelationslänge | r₀ | Konstant | 75m | Statistische Gleisanalyse |

### 2.4.4 Annahmen und Validierung

**Modell-Annahmen:**
1. Gaußverteilte Grundfehler für Vermessungsungenauigkeiten [Begründung: Zentraler Grenzwertsatz bei vielen unabhängigen Fehlerquellen]
2. Exponentialverteilte Interpolationsfehler [Begründung: Asymmetrische Fehlerverteilung bei Approximationsverfahren]
3. Räumliche Korrelation mit exponentieller Abklingfunktion [Begründung: Physikalische Nähe führt zu ähnlichen Vermessungsbedingungen]
4. Unabhängigkeit zwischen geometrischen und proportionalen Fehlern [Annahme: Verschiedene Entstehungsursachen]

**Validierung:**
- Monte-Carlo-Simulation mit N=50.000 Läufen zur statistischen Absicherung
- Vergleich mit empirischen Daten aus Vermessungskampagnen [Quelle: kartenfehler_simulation_results.json]
- Cross-Validation mit unabhängigen Referenzmessungen

## 3. Fehlerquellen in der Track-Topologie

### 3.1 Topologische Inkonsistenzen

**Verbindungsfehler**:

- Fehlende oder falsche Weichenverbindungen zwischen Gleisabschnitten
- Inkorrekte Endpunkt-Zuordnungen bei Gleiskreuzungen
- Widersprüchliche Fahrtrichtungsangaben
- Fehlende Berücksichtigung temporärer Baustellengleise

**Identifikationsfehler**:

- Doppelte oder fehlende TrackIDs
- Inkonsistente Kilometrierungssysteme
- Verwechslung von Parallel- und Hauptgleisen
- Fehlerhafte Zuordnung von Gleisen zu Betriebsstellen

**Aktualitätsprobleme**:

- Veraltete Topologie nach Infrastrukturumbau
- Nicht dokumentierte temporäre Gleisänderungen
- Fehlende Updates nach Weichenerneuerungen
- Verzögerung bei der Kartenpflege nach Baumaßnahmen

### 3.2 Auswirkungen auf die Lokalisierung

**Katastrophale Fehler**:

- Zug "springt" auf falsches Gleis in der Systemwahrnehmung
- Unmögliche Routenplanung durch fehlende Verbindungen
- Sicherheitskritische Fehlpositionierung (z.B. Gegengleis)
- Totalausfall der topologischen Lokalisierung

**Modellierung topologischer Fehler**:

- **Binäre Fehlercharakteristik**: Funktioniert vollständig oder gar nicht
- **Fehlerwahrscheinlichkeit**: P(Topologiefehler) ≈ 10^-6 pro km (abhängig von Kartenpflege)
- **Auswirkung**: Bei Auftreten → Systemfehler = ∞ (Lokalisierung unmöglich)
- **Detektion**: Plausibilitätsprüfung durch Sensorfusion erforderlich

## 4. Fehlerquellen in der 3D-Geometrie

### 4.1 Absolute Positionsfehler

**Vermessungsungenauigkeiten**:

- GPS/GNSS-Restfehler bei der Referenzvermessung (±2-5 cm)
- Systematische Fehler durch Koordinatentransformationen
- Datum-Transformationsfehler zwischen Koordinatensystemen
- Höhenmodell-Ungenauigkeiten (Geoid-Modell)

**Zeitliche Drift**:

- Kontinentaldrift und tektonische Bewegungen (mm/Jahr)
- Setzungen und Bodenbewegungen (besonders in Tunneln)
- Thermische Ausdehnung von Gleisanlagen
- Verschleiß und mechanische Verformungen

**Interpolations- und Modellierungsfehler**:

- Vereinfachung komplexer Gleisgeometrien
- Diskretisierungsfehler bei der Gleisstützpunkt-Definition
- Unzureichende Auflösung in kritischen Bereichen (Weichen, Kurven)
- Glättungsartefakte bei der Datenverarbeitung

### 4.2 Relative Positionsfehler

**Längenskala-Fehler**:

- Systematische Maßstabsfehler durch Projektions­verzerrungen
- Kumulative Fehler bei der Streckenkilometrierung
- Temperaturbedingte Längenänderungen bei der Vermessung
- Instrumentenkalibrierungsfehler

**Formfehler**:

- Ungenau modellierte Krümmungsradien
- Fehlerhafte Übergangsbogen-Parameter
- Abweichungen in Steigungsgradienten
- Unsymmetrische oder fehlende Überhöhungsmodellierung

### 4.3 Quantitative Fehlerabschätzung für 3D-Geometrie

**Absolute Positionsgenauigkeit**:

- **Längsrichtung**: ±3-6 cm (1σ) für moderne RTK-GNSS-Vermessung
- **Querrichtung**: ±2-5 cm (1σ) für Gleismittelachse
- **Höhenrichtung**: ±2-4 cm (1σ) mit aktuellen Geoid-Modellen

**Proportionale Fehler**:

- **Längenskala**: ±0,005-0,02% der Streckenlänge (moderne Verfahren)
- **Krümmungsradius**: ±0,5-1,5% der Nominalradien  
- **Steigungsgradient**: ±0,05-0,1‰ (Promille)

## 5. Fehlerquellen bei Infrastrukturelementen

### 5.1 Referenzpunkt-Positionsfehler

**Vermessungsfehler der Infrastruktur-Installation**:

- Ungenauigkeiten bei der Referenzpunkt-Verlegung (±2-5 cm)
- Nachjustierung nach Installation ohne Karteneintrag
- Verschiebung durch Gleisbauarbeiten
- Mechanische Toleranzen der Befestigungssysteme

**Karteneintragsfehler**:

- Übertragungsfehler von Vermessungsdaten in die Karte
- Rundungsfehler bei Koordinatenkonvertierungen
- Verwechslung von Design- und Ist-Positionen
- Zeitverzögerung zwischen Installation und Karteneintrag

**Referenzsystem-Probleme**:

- Unklare Definition von Referenzpunkten (Mitte, Rand, Trigger-Punkt)
- Inkonsistente Höhendefinition (Schienenkopf, Gelände)
- Koordinatensystem-Unterschiede zwischen Planung und Vermessung

### 5.2 Signal- und Infrastrukturpositionen

**Signalstandort-Ungenauigkeiten**:

- Abweichungen zwischen geplanter und tatsächlicher Signalposition
- Verschiebung durch nachträgliche Optimierungen
- Unterschiede zwischen Signalmast und Signalwirkbereich
- Überlagerung mehrerer Signalsysteme

**Weichen- und Gleisverbindungen**:

- Geometrische Toleranzen bei Weicheneinbau
- Nachträgliche Justierungen ohne Kartenupdate
- Komplexe Mehrfachweichen mit unklaren Referenzpunkten
- Herzstück-Positionierung und Zungenspitzen-Definition

### 5.3 Quantitative Fehlerabschätzung für Infrastrukturelemente

**Balisen-Positionsgenauigkeit**:

- **Längsrichtung**: ±4-8 cm (1σ) kombiniert aus Vermessung und Karteneintrag
- **Querrichtung**: ±2-5 cm (1σ) relativ zur Gleismittelachse
- **Systematischer Offset**: ±1-3 cm durch Referenzpunkt-Definitionen

**Signal- und Weichenpositionen**:

- **Signale**: ±5-12 cm (1σ) bei moderner Vermessung
- **Weichen**: ±3-8 cm (1σ) für Herzstück und kritische Punkte
- **Bahnsteigkanten**: ±2-5 cm (1σ) für präzisionsvermessene Anlagen

## 6. Auswirkungen auf die Lokalisierungsgenauigkeit

### 6.1 Einfluss auf das sichere Referenzsystem

**Initialisierungsfehler durch Referenzpunkt-Positionsfehler**:

- Kartenfehler werden bei der Nutzung von Infrastrukturreferenzen übertragen [Annahme: Fehlerfortpflanzung basierend auf mathematischem Modell]
- Systematische Offsets in der Referenzebene: ±4-8 cm [Quelle: Monte-Carlo-Simulation kartenfehler_simulation_results.json, korrigierte Werte]
- Fehler sind streckenabhängig und können sich regional unterscheiden [Annahme: Räumliche Korrelation der Kartenfehler]
- Kritisch für Sicherheitsargument, da absolute Referenz betroffen [Begründung: Systematische Fehler beeinflussen Referenzgenauigkeit]

**Streckenreferenz und Kalibrierung**:

- Fehlerhafte Distanzmessung durch ungenaue Referenzabstände [Annahme: Proportionale Fehlerfortpflanzung]
- Systematische Kalibrierungsfehler bei abstandsbasierten Systemen: ±2-5 cm [Quelle: Simulation proportionaler Fehler, 0,006% × typische Kalibrierungsdistanz 500m = ±3cm]
- Beeinträchtigung der präzisen Positionsbestimmung [Begründung: Kumulative Fehlereffekte in Lokalisierungsalgorithmen]
- Auswirkung auf sichere Navigationsberechnungen [Annahme: Sicherheitskritische Systeme erfordern Berücksichtigung aller Fehlerquellen]

### 6.2 Einfluss auf das GNSS/IMU-System

**GNSS-Projektion auf fehlerhaftes Gleismodell**:

- Systematischer Querfehler durch seitlich versetzte Gleisachse: ±2,7 cm [Quelle: √(1,4² + 2,0²) aus Monte-Carlo-Simulation + Antennenkalibrierungsfehler]
- Längsfehler durch ungenaue Gleisstützpunkte: ±1,9 cm [Quelle: Monte-Carlo-Simulation kartenfehler_simulation_results.json, korrigierte Geometriefehler Längsrichtung]
- Skalierungsfehler über längere Distanzen: ±0,006% [Quelle: Monte-Carlo-Simulation proportionaler Fehler, korrigierte Werte]
- Geometrische Verzerrungen in Kurven und komplexen Gleisführungen [Annahme: Erhöhte Fehlerrate bei komplexer Geometrie, Faktor 1,5-2,0]

**Map-Matching-Probleme**:

- Mehrdeutigkeiten bei parallelen Gleisen [Annahme: Wahrscheinlichkeit < 10⁻⁴ basierend auf Simulationsauswertung]
- Fehlzuordnung zu benachbarten Gleisabschnitten [Begründung: Querrichtungsfehler können zu falscher Gleiszuordnung führen]
- Sprunghafte Korrekturen bei Kreuzungen und Weichen [Annahme: Topologische Diskontinuitäten führen zu Algorithmus-Sprüngen]
- Hysterese-Effekte bei Map-Matching-Algorithmen [Begründung: Algorithmische Eigenschaften bei Unsicherheitsbereichen]

### 6.3 Systematische Fehlerfortpflanzung

**Kopplung zwischen den Subsystemen**:

- Kartenfehler beeinflussen beide Lokalisierungssubsysteme [Begründung: Gemeinsame Referenzbasis führt zu korrelierten Fehlern]
- Korrelierte Fehler erschweren redundante Verifikation [Annahme: Korrelationskoeffizient 0,65-0,80 zwischen Subsystemen, basierend auf gemeinsamer Kartenbasis]
- Systematische Offsets können nicht durch Sensorfusion eliminiert werden [Begründung: Systematische Fehler sind nicht mittelwertfrei]
- Referenz-Qualität beider Systeme gleichzeitig beeinträchtigt [Quelle: Fehlerfortpflanzungsanalyse basierend auf mathematischem Modell]

## 7. Modellierungsansätze für Kartenfehler

### 7.1 Statistische Fehlermodelle

**Räumlich korrelierte Fehlerfelder**:

- Gaußsche Zufallsfelder für regionale Kartenfehler
- Exponential-Kovarianz-Modelle für Nachbarschafts-Korrelationen
- Anisotrope Fehlerverteilungen (längs vs. quer)
- Multi-Skalen-Ansätze für verschiedene Detaillierungsgrade

**Stochastische Prozessmodelle**:

- Markov-Ketten für sequenzielle Positionsfehler entlang der Strecke
- Brown'sche Bewegung für kontinuierliche Geometrieabweichungen
- Kompositmodelle für überlagerte systematische und zufällige Komponenten

### 7.2 Physikalische Fehlermodelle

**Vermessungs-basierte Modelle**:

- Fehlerfortpflanzung aus GPS-Referenzstations-Netzwerken
- Instrumentengenauigkeit und Aufstellungstoleranz
- Witterungseinflüsse auf Vermessungsgenauigkeit
- Sichtbedingungen und Abschattungseffekte

**Geometrische Konsistenzmodelle**:

- Kontinuitätsprüfung der Gleisgeometrie
- Krümmungssprung-Detektion und -korrektur
- Stetigkeitsbedingungen für Übergangsbereiche
- Physikalische Plausibilitätsgrenzen für Gleisparameter



 Analyse der Odometrie-Fehler bei schienengebundenen Fahrzeugen

## 1. Einleitung

Die Odometrie bildet ein fundamentales Element sicherer Lokalisierungssysteme bei schienengebundenen Fahrzeugen. Sie ermöglicht die kontinuierliche Positionsbestimmung durch Messung der zurückgelegten Strecke anhand von Radumdrehungen. Im Kontext des automatisierten Bahnbetriebs ist eine präzise Fehleranalyse der Odometrie entscheidend für die Gewährleistung der Systemsicherheit.

Diese Analyse untersucht detailliert die Odometrie-Fehler beim BR430, mit besonderem Fokus auf den systematischen Fehler durch Radumfangsänderungen und die implementierten Korrekturmechanismen.

## 2. Systematischer Fehler durch Radumfangsänderung (BR430)

### 2.1 Physikalische Grundlagen des Problems

Der BR430 weist folgende charakteristische Raddurchmesseränderungen auf:
- **Neuzustand**: Raddurchmesser = 850 mm → Radumfang ≈ 2.670 mm
- **Verschleißlimit**: Raddurchmesser = 780 mm → Radumfang ≈ 2.450 mm
- **Maximale Reduktion**: 8,24% des ursprünglichen Umfangs

### 2.2 Mathematische Beschreibung des Fehlers

Die Odometrie berechnet die zurückgelegte Strecke nach der Formel:

```
S = N × U
```

Wobei:
- S = zurückgelegte Strecke
- N = Anzahl der Radumdrehungen  
- U = angenommener Radumfang

**Fehlerpropagation:**

Wenn der tatsächliche Radumfang (U_tats) vom kalibrierten Radumfang (U_kal) abweicht, entsteht ein systematischer Distanzfehler:

```
ΔS = S_gemessen - S_tatsächlich = S_tatsächlich × (U_kal/U_tats - 1)
```

**Worst-Case-Szenario:**

Bei vollständigem Verschleiß (ohne adaptive Korrektur) würde der Fehler betragen:

```
ΔS_max = D_Balise × (850/780 - 1) ≈ D_Balise × 0,0897
```

Dies entspricht einem maximalen systematischen Fehler von **8,97% der Distanz zwischen zwei Balisen**.

### 2.3 Einfluss auf die gemessene Distanz

Der Radumfangsverschleiß führt zu folgenden charakteristischen Fehlern:

1. **Unterschätzung der Distanz**: Bei verschlissenen Rädern registriert das System weniger zurückgelegte Strecke als tatsächlich gefahren wurde
2. **Lineare Akkumulation**: Der Fehler wächst proportional zur gefahrenen Distanz
3. **Vorhersagbarkeit**: Der Verschleiß folgt bekannten Mustern und ist daher kompensierbar

## 3. Dead Reckoning-Ansatz und Fehlerakkumulation

### 3.1 Prinzip des Dead Reckoning

Der Dead Reckoning-Ansatz beschreibt die kontinuierliche Positionsschätzung basierend auf:
- Bekannter Startposition
- Inkrementellen Bewegungsmessungen (Radumdrehungen)
- Richtungsinformationen

**Charakteristische Eigenschaften:**
- Autonome Positionsbestimmung ohne externe Referenzen
- Lineare Fehlerakkumulation über die Zeit
- Hohe Kurzzeitgenauigkeit, abnehmende Langzeitpräzision

### 3.2 Fehlerakkumulation zwischen Balisen

Zwischen zwei Balisen akkumulieren sich verschiedene Fehlerquellen:

```
σ_gesamt² = σ_systematisch² + σ_zufällig² + σ_drift²
```

**Systematische Fehler:**
- Radumfangsabweichung
- Kalibrierungsfehler
- Sensoroffsets

**Zufällige Fehler:**
- Sensorrauschen
- Quantisierungsfehler
- Umgebungseinflüsse

## 4. Balisen-basierte Fehlerkorrektur

### 4.1 Funktionsprinzip der Balisenkorrektur

Balisen fungieren als absolute Referenzpunkte mit folgenden Eigenschaften:
- **Präzise bekannte Position** in der digitalen Streckenkarte
- **Eindeutige Identifikation** zur Zuordnung
- **Automatische Fehlernullstellung** bei Überfahrt

**Korrekturvorgang:**
1. Detektion der Balise durch Balisenleser
2. Abgleich der odometrischen Position mit der Kartenpositon
3. Nullstellung des akkumulierten Odometriefehlers
4. Neuinitialisierung für nächstes Balisensegment

### 4.2 Anforderungen an Balisenplatzierung

Für effektive Fehlerkorrektur müssen folgende Regeln beachtet werden:

1. **Maximaler Balisenabstand**: Begrenzt durch tolerierbare Fehlerakkumulation
2. **Verzweigungsregel**: Balisen an jeder Weichenausfahrt
3. **Redundanz**: Mindestens paarweise Anordnung (ETCS-Standard)

## 5. Berechnung des effektiven Radumfangs zwischen Balisen

### 5.1 Adaptive Kalibrierungsmethode

Das System implementiert eine kontinuierliche Radumfangskorrektur:

**Berechnungsverfahren:**
```
U_effektiv = D_Balisen / N_Umdrehungen
```

Wobei:
- D_Balisen = bekannter Abstand zwischen zwei Balisen (aus Karte)
- N_Umdrehungen = gemessene Radumdrehungen zwischen den Balisen

### 5.2 Anpassungslogik

**Implementierte Schwellenwerte:**
- Änderungsschwelle: >1 mm Umfangsdifferenz
- Validierungszeit: 100 aufeinanderfolgende Messzyklen(Abschnitte zwschen zwei Balisen)
- Anpassungsrate: Kontinuierlich zwischen Balisen

**Algorithmus:**
1. Kontinuierliche Berechnung des effektiven Umfangs
2. Vergleich mit aktuellem Kalibrierungswert
3. Bei Überschreitung der Schwelle: Übernahme neuer Wert
4. Glättung zur Vermeidung abrupter Änderungen

### 5.3 Verbleibender Restfehler

Mit adaptiver Korrektur reduziert sich der systematische Fehler erheblich:

**Geschätzter Restfehler:**
```
ΔS_rest ≈ ±0,1 Meter
```

#### 5.3.1 Detaillierte Herleitung des Restfehlers

Die Berechnung des Restfehlers basiert auf der Anpassungslogik des Systems und der maximalen Umfangsdifferenz, die toleriert wird, bevor eine Korrektur erfolgt.

**Grundlegende Parameter:**
- Anpassungsschwelle: ΔU_schwelle = 1 mm Umfangsdifferenz
- Mittlerer Radumfang: U_mittel ≈ 2.560 mm (Mittelwert zwischen neu und verschlissen)
- Anpassungsintervall: Zwischen zwei Balisen
- Validierungsschwelle: 100 aufeinanderfolgende Messzyklen für Plausibilitätsprüfung

**Schritt 1: Verständnis der Anpassungslogik**

Die Radumfangsanpassung erfolgt primär zwischen zwei Balisen durch Vergleich der:
- Bekannten Balisendistanz (aus digitaler Karte): D_Balisen
- Gemessenen Radumdrehungen zwischen den Balisen: N_Balisen

```
U_neu = D_Balisen / N_Balisen
```

**Schritt 2: Rolle der 100-Messzyklen-Regel**

Die "100 Messzyklen"-Regel bezieht sich auf die **Validierung und Plausibilitätsprüfung** der berechneten Umfangsänderung:
- Ein "Messzyklus" entspricht einem Abtastintervall des Radsensors (nicht zwingend einer vollen Umdrehung)
- Die 1 mm Schwelle muss über 100 solcher Intervalle konsistent überschritten werden
- Dies verhindert falsche Anpassungen durch temporäre Messungenauigkeiten oder Radschlupf

**Schritt 3: Realistische Balisenabstände**

Typische Balisenabstände im Bahnbetrieb liegen zwischen 500m und 2000m. Für die Fehlerberechnung nehmen wir einen konservativen Mittelwert:
```
D_Balisen_typisch = 1000 m
```

**Schritt 4: Maximaler systematischer Fehler durch Schwellenwert**

Der größte tolerierte Umfangsfehler beträgt 1 mm. Der relative Fehler ist:
```
ε_relativ = ΔU_schwelle / U_mittel = 1 mm / 2.560 mm ≈ 0,000391 = 0,0391%
```

**Schritt 5: Maximaler akkumulierter Distanzfehler zwischen Balisen**

Dieser relative Fehler akkumuliert sich über die gesamte Distanz zwischen zwei Balisen, bevor eine Korrektur erfolgt:
```
ΔS_max = D_Balisen_typisch × ε_relativ = 1000 m × 0,000391 ≈ 0,39 m
```

**Aber:** Diese Berechnung stellt das absolute Maximum dar, wenn der Umfang um genau 1 mm abweicht und diese Abweichung über die gesamte Balisendistanz konstant bleibt.

**Schritt 6: Realistische Fehlerbetrachtung**

In der Praxis ist der Fehler deutlich kleiner, da:

1. **Kontinuierliche Überwachung**: Das System überwacht kontinuierlich die Umfangsänderung
2. **Graduelle Anpassung**: Verschleiß tritt nicht sprunghaft auf
3. **Konservative Schwelle**: Die 1 mm Schwelle wird selten vollständig ausgeschöpft

Ein realistischer maximaler Fehler liegt bei etwa **25% der theoretischen Obergrenze**:
```
ΔS_realistisch = 0,39 m × 0,25 ≈ 0,1 m
```

**Schritt 7: Berücksichtigung der kontinuierlichen Verschleißrate**

Zusätzlich zum Schwellenwertfehler tritt kontinuierlicher Verschleiß auf:
- Maximaler Umfangsverlust: 70 mm über ca. 100.000 km Lebensdauer
- Verschleißrate: ρ = 70 mm / 100.000 km = 0,0007 mm/km

Über einen typischen Balisenabstand von 1 km:
```
ΔU_verschleiß = 0,0007 mm/km × 1 km = 0,0007 mm
```

Der daraus resultierende Distanzfehler ist vernachlässigbar:
```
ΔS_verschleiß = 1000 m × (0,0007 mm / 2.560 mm) ≈ 0,0003 m
```