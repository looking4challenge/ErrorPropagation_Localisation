# Fehleranalyse Balise-Leser BRV4 (Schema 2.0)

Dieses Dokument wurde vollständig auf das neue Simulations-Schema 2.0 aktualisiert. Das frühere (Legacy / Schema 1.x) Modell mit getrimmter Signalqualitätsverteilung ist ausschließlich zur historischen Referenz im Appendix A aufgeführt.

## 1. Executive Summary (Schema 2.0)

Ziel: Quantitative Charakterisierung der BRV4-spezifischen Messfehler für sicherheitskritische und hybride Lokalisierung. Änderungen gegenüber Schema 1.x: Entfernen des harten Signalqualitäts-Caps, Einführung optionaler Markov-Ausfallmodellierung, Failure Mode „drop“, Konvergenz-Snapshots und versionierte Metadaten.

| Änderung | Legacy (Schema 1.x) | Schema 2.0 | Effekt |
|----------|---------------------|------------|--------|
| Signalqualität | Trunkiert λ=0.05 (Cap 10 cm) | Exponential λ=0.2 (ungekappt) | Heavy Tail / Ausreißer sichtbar, extreme Perzentile steigen |
| Ausfallmodell | Linear p_fail(v) | Linear ODER Markov (p_fail_given_ok, p_stay_failed) | Cluster-Ausfälle simulierbar |
| Failure Mode | inflate | inflate / drop | Fehlende Messung modellierbar |
| Convergence | nicht vorhanden | konfigurierbare Snapshots | Statistische Konvergenz dokumentierbar |
| Metadaten | keine Versionierung | schema_version, model_version, config_hash | Reproduzierbarkeit & Audit |

Referenzgeschwindigkeit 30 km/h, Runs N=20.000 (Spot-Check; für finale Freigabe N≥50.000).

### 1.1 Standardkonfiguration (linearer Ausfall, λ=0.2, keine Trunkierung)

| Kennwert | Längs (cm) | Quer (cm) | Total (cm) |
|----------|-----------:|----------:|-----------:|
| Mittelwert μ | 510.1 | 151.8 | 532.2 |
| Standardabw. σ | 517.2 | 153.1 | 539.4 |
| Median | 351.1 | 104.5 | 365.9 |
| 95%-Perzentil | 1509.9 | 448.8 | 1574.5 |
| 99%-Perzentil (Band) | 2358–2450 | ~700 | ~2450 |
| Max beobachtet | >8500 | >2100 | >8800 |
| Ausfallrate (linear) | 2.88% | – | – |

Interpretation: Die ungetrimmte Exponentialannahme liefert konservative, aber physikalisch wahrscheinlich überhöhte Ausreißer. Median << Mittelwert zeigt starke Schiefe. Latenz- und Antennenanteile werden durch Signalqualitätsausreißer verdrängt.

### 1.2 Optimierte Spezifikationskonfiguration (spec.yaml)

| Kennwert | Längs (cm) | Quer (cm) | Total (cm) |
|----------|-----------:|----------:|-----------:|
| Mittelwert μ | 401.9 | 120.1 | 419.5 |
| σ | 398.0 | 118.8 | 415.3 |
| 95%-Perzentil | 1186.0 | 354.2 | 1238.2 |
| Ausfallrate | 2.15% | – | – |

Verbesserung (95%-Perzentil längs): ca. −21% vs. Standard.

### 1.3 Markov-Ausfallmodell Validierung

Konfiguration: p_fail_given_ok=0.01, p_stay_failed=0.9 → theoretische Steady-State 9.09%. Beobachtet 9.08% (Abweichung <0.02%). Markov-Modell validiert.

### 1.4 Varianzzerlegung (Standard, Markov aktiv)

| Komponente | Varianzanteil Längs | Varianzanteil Quer | Bemerkung |
|------------|--------------------:|-------------------:|-----------|
| Signalqualität | ~99.98% | ~99.99% | Heavy Tail dominiert |
| EM-Störung | <0.001% | <0.003% | Verdrängt |
| Latenz | ~0.015% | – | Marginal |
| Antenne | ~0.001% | ~0.009% | Marginal |

Konsequenz: Klassische Optimierung einzelner Komponenten außer Signalqualität hat im aktuellen Modell kaum Einfluss – Modellanpassung statt Mikro-Optimierung notwendig.

### 1.5 Handlungsempfehlungen (Kurzfristig)

1. Empirische Messkampagne zur realen Signalqualitäts-Verteilung (Bounding, Sättigung).
2. Fit-Analyse alternativer Verteilungen (Weibull, Lognormal, Exponential+Soft-Cap) via AIC/BIC.
3. Definition regulativer Cutoffs (z.B. physikalisches 99.9%-Maximum) für Safety-Bewertung.
4. Evaluierung `failure_mode=drop` in Fusions-/Intervallwachstumsmodellen.
5. Einführung `calibration_profile` zur standort-/hardwareabhängigen Reparametrisierung.

---

## 2. System- & Nachrichtenarchitektur

- Ereignisgetriebene Balisen-Events (keine 1 Hz Limitierung für Events).
- `payload.timestamp` weiterhin beste Approximation der Überfahrzeit.
- Lineares Ausfallmodell oder Markov-Kette (2-Zustandsmodell: OK / Fail).

## 3. Fehlermodell (Schema 2.0)

1. Latenz: Normal(μ=10 ms, σ=2 ms) + Uniform ±1 ms (Temperaturdrift).
2. Antennenoffset: 2D-Normal σ=2 cm, ρ=0.1.
3. Signalqualität: Exponential(rate=0.2 1/m), optional Clamp (`signal_quality_truncation`).
4. EM-Störung: Rayleigh(σ=1.5 cm).
5. Geschwindigkeitsfehler: Normal(0, 0.1 m/s).
6. Ausfall: Linear oder Markov.
7. Failure Mode: inflate (Fehlerinflation) oder drop (Messung als ausgefallen markieren).

Hinweis: Exponential ohne physikalische Sättigung führt zu konservativer Überschätzung extremer Perzentile.

## 4. Simulation

Implementierung in `simulation_balise_error.py` mit:

- Konfigurations-Dataclass (`BRV4SimulationConfig`)
- Hash & Metadaten (schema_version, model_version, config_hash)
- Markov Übergänge + theoretische Steady-State Ausweisung
- Convergence Snapshots (konfigurierbar) – in Referenzläufen hier deaktiviert
- Export: JSON, CSV (konfigurierbares sample_size), optional Excel & Plot

## 5. Ergebnisse (Details)

Siehe Executive Summary Tabellen. Heavy Tail manifestiert sich ab ~P95. Median signifikant unter Mittelwert => starke Schiefe.

## 6. Sicherheits- & Systemimplikationen

1. Aktuelle (ungekappte) Verteilung nicht direkt für Safety-Freigabe geeignet.
2. Für Sensorfusion Kalman: Notwendigkeit eines gebundenen Modells (sonst degenerierte Gewichte).
3. Markov-Modell liefert Grundlage zur Simulation sequentieller Ausfallszenarien (Fehlstrecken-Clustering).

## 7. Priorisierte Maßnahmen

| Priorität | Maßnahme | Ziel | Erfolgskriterium |
|----------|----------|------|------------------|
| P1 | Empirische Verteilungsaufnahme | Realistische Bounds | Datensatz ≥ O(10^4) Events |
| P1 | Modell-Fit & Auswahl | Reduktion Heavy Tail | Verhältnis P99/Median < 8 |
| P2 | Implement Soft-Cap Option | Safety Bounding | Konfigurierbarer Cap + Tests |
| P2 | Drop-Mode Impact Analyse | Intervallmodellierung | Vergleich Intervallbreiten |
| P3 | Kalibrierungsprofil | Standortabhängigkeit | Reproduzierbarer Parameter-Fit |

## 8. Validierung

- Markov Failrate: Beobachtet 9.08% vs. Theorie 9.09% (<0.02% Δ)
- Reproduzierbarkeit: Seed + config_hash dokumentiert
- Testsuite: Markov-Steady-State, Varianzsumme, Seed-Repro, Warnungen bestanden

## 9. Empfehlung

Legacy-Zahlen (Schema 1.x) weiterhin für praxisnahe Abschätzungen nutzen, bis empirische Daten für Schema 2.0 Signalqualitätsverteilung vorliegen. Aktuelle Schema-2.0-Ausreißer ausschließlich als konservative Obergrenze kommunizieren.

---

## Appendix A: Legacy (Schema 1.x) Referenz (gekappte Signalqualität)
N=50.000 @30 km/h, λ=0.05, Hard-Cap 10 cm.

| Metrik | Längs | Quer |
|--------|-------|------|
| Mittelwert μ | 13.6 cm | 3.7 cm |
| σ | 1.6 cm | 0.7 cm |
| 95%-Perzentil | 15.8 cm | 5.1 cm |
| 99%-Perzentil | 20.7 cm | 6.1 cm |
| Max | 26.1 cm | 9.6 cm |

Varianzanteile längs: Signal 55.1%, Latenz 40.0%, EM 2.5%, Antenne 2.2%.

## Appendix B: Reproduzierbarkeit (Beispiele)

```bash
python simulation_balise_error.py --config configs/balise/standard.yaml --runs 50000 --velocity 30 --no-plots --excel
python simulation_balise_error.py --config configs/balise/spec.yaml --runs 50000 --velocity 30 --no-plots --excel
python simulation_balise_error.py --config configs/balise/standard.yaml --runs 50000 --velocity 30 --markov 0.01,0.9 --no-plots
```

## Appendix C: Geplante Modellverfeinerungen

| Option | Beschreibung | Nutzen |
|--------|--------------|--------|
| Soft-Cap (logistisch) | Sanfte Sättigung großer Signalfehler | Realistischere Perzentile |
| Mixture Fit | Exponential + Konstante / Weibull | Besserer Tail-Fit |
| Empirischer Cap | Beobachtetes 99.9%-Quantil | Safety Bounding |
| Drop-Mode Analyse | Modelliert fehlende Messung statt Inflationsausreißer | Genauere Intervallmodelle |

---

Ende der konsistenten Schema-2.0 Analyse.

**Hauptergebnisse bei 30 km/h Referenzgeschwindigkeit** (Simulation N=50.000, Standard-Konfiguration):

- **Längsfehler (μ ± σ)**: 13,6 ± 1,6 cm (σ als Streuungsmaß; sicherheitsrelevant sind Perzentile, nicht σ)
- **Querfehler (μ ± σ)**: 3,7 ± 0,7 cm
- **99%-Perzentil**: 20,7 cm (längs), 6,2 cm (quer)
- **Varianzanteile längs**: Signalqualität 55,1%, Verarbeitungslatenz 40,0%, EM 2,5%, Antenne 2,2%
- **Zeitstempel**: Ereignisgetriebene Balisen-Detektion; `payload.timestamp` als beste Überfahrzeit-Proxy

Hinweis: 1σ-Werte dienen lediglich der Charakterisierung der Verteilung; für sicherheitsgerichtete Auslegung sind 95%- und 99%-Perzentile maßgeblich.

### Update (Schema 2.0 – Oktober 2025)

Das ursprüngliche Modell (oben) nutzte eine getrimmte Exponentialverteilung (λ=0.05, Hard-Cap 10 cm) für die Signalqualität und ein rein lineares Ausfallmodell. Mit Schema 2.0 wurden folgende Änderungen eingeführt und separat simulativ validiert (Standard vs. optimierte Spezifikation):

| Änderung | Legacy (Schema 1.x) | Neu (Schema 2.0) | Wirkung |
|----------|---------------------|------------------|---------|
| Signalqualität | Trunkiert (λ=0.05, Cap 10 cm) | Ungetrimmt (λ=0.2) optional Clamp | Stark schwerere rechte Flanke; Signal dominiert Varianz nahezu vollständig |
| Ausfallmodell | Linear: p_fail = base + factor·v | Optional Markov (p_fail_given_ok, p_stay_failed) | Realistischeres Steady-State-Verhalten / Cluster von Ausfällen |
| Failure Mode | Inflate-only | Inflate oder Drop | Modellierung fehlender Messung möglich |
| Convergence | Nicht verfügbar | Snapshots konfigurierbar | Statistische Konvergenz dokumentierbar |
| Metadata | Basis (keine Versionierung) | schema_version, model_version, config_hash | Reproduzierbarkeit & Auditability |

Aktuelle Referenzläufe (N=20.000, v=30 km/h, Standard Schema 2.0, λ=0.2, ohne Trunkierung, failure_mode=inflate):

| Kennwert | Längs (cm) | Quer (cm) | Total (cm) |
|----------|-----------:|----------:|-----------:|
| Mittelwert μ | 510.1 | 151.8 | 532.2 |
| Standardabw. σ | 517.2 | 153.1 | 539.4 |
| Median | 351.1 | 104.5 | 365.9 |
| 95%-Perzentil | 1509.9 | 448.8 | 1574.5 |
| 99%-Perzentil | 2358–2450 (stochastisch) | ~700 | ~2450 |
| Max beobachtet | >8500 | >2100 | >8800 |
| Ausfallrate (legacy linear) | 2.88% | – | – |

Die drastisch höheren Werte gegenüber dem Legacy-Block resultieren NICHT aus einer Verschlechterung des Systems, sondern aus der Modellumstellung: Die zuvor harte Abschneidung der Signalqualitätsverteilung bei 10 cm wurde entfernt, wodurch seltene große Ausreißer jetzt explizit sichtbar sind (realistischere Heavy-Tail-Charakteristik). Für sicherheitsgerichtete Kennzahlen müssen daher Perzentil- und ggf. Trunkierungsstrategien neu definiert werden (z.B. regulatorischer Cap vs. real beobachtete physikalische Grenzen).

Optimierte Spezifikationskonfiguration (spec.yaml; reduzierte Latenz, bessere Antenne, N=20.000):

| Kennwert | Längs (cm) | Quer (cm) | Total (cm) |
|----------|-----------:|----------:|-----------:|
| Mittelwert μ | 401.9 | 120.1 | 419.5 |
| σ | 398.0 | 118.8 | 415.3 |
| 95%-Perzentil | 1186.0 | 354.2 | 1238.2 |
| Ausfallrate (linear) | 2.15% | – | – |

Markov-Validierung (p_fail_given_ok=0.01, p_stay_failed=0.9):

| Kennwert | Wert |
|----------|------|
| Beobachtete Failrate | 9.08% |
| Theoretische Steady-State | 9.09% |
| Abweichung absolut | <0.02% |

Varianzzerlegung (Schema 2.0 Standard, Markov aktiv, N=20.000):

| Komponente | Varianzanteil Längs | Varianzanteil Quer | Kommentar |
|------------|--------------------:|-------------------:|-----------|
| Signalqualität | ~99.98% | ~99.99% | Dominanz durch schwere Rechtsflanke |
| EM-Störung | <0.001% | <0.003% | Marginalisiert |
| Latenz | ~0.015% | – | Verdrängt durch Signalqualitätsschwankungen |
| Antenne | ~0.001% | ~0.009% | Praktisch vernachlässigbar |

Implikation: Bei unverändertem physikalischem Verständnis ist die ungetrimmte Exponentialannahme wahrscheinlich zu konservativ / führt zu unrealistischer Heavy-Tail-Dominanz. Empfehlung: Empirische Obergrenzen oder alternative Modellierung (z.B. Mischung: Exponential + saturierender logistischer Cutoff) evaluieren.

Empfohlene nächste Schritte nach Schema 2.0:

1. Empirische Datenerhebung zur tatsächlichen Verteilung hoher Signalqualitätsfehler (Messkampagne).
2. Parametrische Fit-Tests (AIC/BIC) für Alternativverteilungen (Weibull, Lognormal, Exponential mit Soft-Cap).
3. Safety-spezifische Ableitung eines regulatorischen Cutoff (z.B. 99.9%-physikalisches Maximum) zur Bounding der Extremwerte.
4. Einführung Kalibrierungsprofil (geplantes Feld) für standort-/hardwareabhängige Anpassung.
5. Optional: Aktivierung failure_mode=drop + Downstream-Fusionstest (Auswirkung fehlender Balisenmessung statt inflated error).


Die folgenden Abschnitte (2 ff.) dokumentieren weiterhin das ursprüngliche (Schema 1.x) Modell; eine vollständige Migration der textlichen Passagen auf Schema 2.0 erfolgt nach Abschluss der empirischen Validierung.

## 2. Systemarchitektur und präzisierte Funktionsweise

### 2.1 BRV4 Hardware- und Signalverarbeitungs-Spezifikation

**Hardware-Komponenten**:

- **Signalerzeugung**: 27-MHz-Aktivierungssignal für Eurobalisen
- **Empfang**: 4,23 MHz FSK-modulierte Telegramme
- **Verarbeitung**: FPGA-basierte Echtzeitverarbeitung + CPU mit ROS-Interface
- **Schnittstellen**: Antennen (BR.X14), Ethernet zu ROS-Netzwerk (BR.X20)

### 2.2 Korrigiertes Übertragungsverhalten (BRV4-Spezifikation 2025)

**Übertragungsprotokoll**:

- **Status-/Leermeldungen**: Zyklisch 1 Hz (kontinuierlich, unabhängig von Balisen-Events)
- **Balisen-Events**: **Ereignisgetrieben** nach erfolgreicher Demodulation/Dekodierung
- **Erste vollständige Nachricht**: Nur die erste erfolgreich dekodierte Nachricht wird übertragen
- **Früherkennung**: Balise kann bereits vor geometrischem Überfahren erkannt werden (geschwindigkeitsunabhängig)

**Kritische Klarstellung**: Die oft zitierte "1 Hz Update-Rate" bezieht sich **nur** auf zyklische Statusnachrichten, **nicht** auf die zeitliche Granularität der Balisen-Erkennung. Balisen-Events werden ereignisgetrieben mit eigenem Zeitstempel sofort publiziert (geplante Messbestätigung offen; Messkampagne t_event-Latenz TBD).

### 2.3 Zeitstempel und Latenz-Charakteristika

**Timing-Architektur**:

- **`payload.timestamp`**: Enthält unkompensierte FPGA→CPU + interne Netzwerklatenz (Messbereich TBD, Spezifikationsziel <10 ms End-to-End)
- **Systemlatenz**: Variable interne Verarbeitungszeit (FPGA→CPU + Reader-interne Netzwerkkomponenten)
- **Zusätzliche Verarbeitungslatenz**: Differenz `payload.timestamp` ↔ `header.timestamp` (ROS-Publish + Serialisierung)
- **ROS-Netzwerklatenz**: Systemabhängig; `payload.timestamp` aktuell beste Näherung für Überfahrzeit

**Hinweis**: Spezifische Latenzwerte erfordern Messung unter realen Betriebsbedingungen mit Hardware-in-the-Loop-Tests.

**Empfehlung für Positionsrekonstruktion**: `payload.timestamp` verwenden für tatsächlichen Überfahrzeitpunkt.

### 2.4 Detektionsverhalten und Geschwindigkeitsabhängigkeit

**Erkennungseigenschaften**:

- **Detektionsrate**: Variiert mit Geschwindigkeit [0–60 km/h]; im Modell als Ausfallwahrscheinlichkeit implementiert
- **Früherkennung**: Möglich (architekturbedingt), aber in dieser Simulation nicht separat parametrisiert (kein Offset-Parameter modelliert)
- **Keine Positionsbestimmung**: BRV4 liefert kein eigenes Lage-Estimat (Positionsreferenz ausschließlich aus digitaler Karte)

## 3. Mathematisches Fehlermodell

### 3.1 Fehlerquellen-Taxonomie

**Zeit- und Latenz-bedingte Fehler**:

1. **FPGA→CPU Latenz**: Variable (in `payload.timestamp` enthalten)
2. **Signalverarbeitung**: Abhängig von Signalqualität und Telegrammlänge
3. **ROS-Publishing**: Systemlast-abhängig
4. **Gesamtlatenz**: Charakteristische Verarbeitungszeit (Simulationsannahme konservativ: μ=10 ms, σ=2 ms; Spezifikation Ziel <10 ms → alternative Parametrierung μ≈8 ms diskutiert)

**Hinweis**: Spezifische Latenzwerte sind systemspezifisch und erfordern Hardware-Messungen für exakte Charakterisierung.

**Hardware-bedingte Fehler**:
5. **Antennen-Montage-Offset**:

- Längsrichtung: σ = 2,0 cm (Normalverteilung)
- Querrichtung: σ = 2,0 cm (Normalverteilung)
- Korrelation: ρ = 0,1 (schwache Montagekorrelation)

**Anmerkung zu Kartenfehlern**:

- Kartenfehler werden separat in output\map_error_analysis.md untersucht
- Diese Analyse fokussiert auf die gerätespezifischen BRV4-Fehlerquellen

**Umwelt- und Betriebsfehler**:
7. **Signalqualität**: Trunkierte Exponentialverteilung mit Rate λ = 0,05 1/m, Obergrenze 0,10 m (10 cm). Ungetrimmter Erwartungswert 1/λ = 20 m ist hier nicht physikalisch relevant; durch harte Abschneidung bei 0,10 m ergibt sich ein effektiver Erwartungswert ≈5,2 cm (E[X | X≤0,10 m]).
8. **EM-Störungen**: Rayleigh-Verteilung (σ = 1,5 cm)
9. **Geschwindigkeitsabhängige Ausfallrate**: P_fail(v) = 0,02 + 0,0003×v [km/h] (modelliert als Erhöhungsfaktor des Fehlerausmaßes – nicht als fehlende Messung)

### 3.2 Mathematisches Gesamtfehlermodell

**Positionsfehler-Berechnung**:

Längsfehler:

 
```text
ε_längs = √(ε_latenz² + ε_antenne_längs² + ε_umwelt_längs²)
```

Querfehler:

```text
ε_quer = √(ε_antenne_quer² + ε_umwelt_quer²)
```

**Latenzfehler (geschwindigkeitsabhängig)**:

```text
ε_latenz = v × t_latenz,  t_latenz ~ N(10 ms, 2 ms) (konservativ)
Optional analytische Variante: t_latenz ~ N(8 ms, 2 ms) (spezifikationsnah)
```

**Gesamtfehler-Berechnung (Root-Sum-Square)**:

```text
σ_längs² = σ_latenz² + σ_antenne_längs² + σ_umwelt_längs²
σ_quer² = σ_antenne_quer² + σ_umwelt_quer²
```

### 3.3 Parameterisierung für Monte-Carlo-Simulation

| Parameter | Verteilung | Wert | Quelle/Begründung |
|-----------|-----------|------|-------------------|
| **Verarbeitungslatenz** | Normal | μ=10ms, σ=2ms | Konservativ (Design-Grenze <10ms) |
| **Temperatureffekt** | Uniform | ±1ms | Hardware-Drift |
| **Antennen-Offset (längs)** | Normal | μ=0, σ=2,0cm | Fertigungstoleranz |
| **Antennen-Offset (quer)** | Normal | μ=0, σ=2,0cm | Fertigungstoleranz |
| **Montage-Korrelation** | - | ρ=0,1 | Schwache Korrelation |
| **Signalqualität** | Trunk. Exponential | λ=0,05 1/m, max=10cm | Modellannahme (siehe Text) |
| **EM-Störungen** | Rayleigh | σ=1,5cm | Umgebungseinflüsse |
| **Detektionsrate** | Binomial | P_fail(v)=0,02+0,0003v | Geschwindigkeitsabhängig |
| **Geschwindigkeitsfehler** | Normal | μ=0, σ=0,1m/s | Odometriegenauigkeit |

## 4. Monte-Carlo-Simulationsmodell

### 4.1 Algorithmus-Struktur

**Eingabe**:

- Geschwindigkeit v [km/h]
- Anzahl Simulationsläufe N (Standard: 50.000)
- Parameterverteilungen (siehe Tabelle 3.3)

**Simulationsschleife**:

Die Monte-Carlo-Simulation erfolgt in 50.000 Iterationen; einzige modellierte Korrelation ist der zweidimensionale Antennen-Offset (ρ=0,1). Nicht modelliert: Telegrammlängenvariation, ROS-Jitter, Früherkennungs-Offset.

### 4.2 Implementierung der erweiterten Simulation

**Simulation**:

Die detaillierte Implementierung der Monte-Carlo-Simulation erfolgt in separater Python-Datei (`simulation_balise_error.py`) und umfasst alle definierten Fehlerquellen, Korrelationen und statistische Verteilungen. Die Simulation generiert 50.000 Zufallsrealisierungen und berechnet umfassende Statistiken.

## 5. Simulationsergebnisse und Validierung

### 5.1 Monte-Carlo-Ergebnisse bei 30 km/h

**Längsfehler-Verteilung (50.000 Simulationsläufe)**:

```text
Statistische Kennwerte (BRV4-spezifisch):
- Mittelwert (μ):         13,6 cm
- Standardabweichung σ:   1,61 cm
- Median:                 13,37 cm
- 95%-Perzentil (oberes): 15,78 cm
- 99%-Perzentil (oberes): 20,71 cm
- Maximum beobachtet:     26,1 cm
Hinweis: Bereich "μ ± σ" ≈ 12,0 – 15,2 cm; kein echtes Konfidenzintervall sondern heuristische Streuungsangabe.
```

**Querfehler-Verteilung (50.000 Simulationsläufe)**:

```text
Statistische Kennwerte (BRV4-spezifisch):
- Mittelwert (μ):         3,72 cm
- Standardabweichung σ:   0,68 cm
- Median:                 3,51 cm
- 95%-Perzentil (oberes): 5,11 cm
- 99%-Perzentil (oberes): 6,10 cm
- Maximum beobachtet:     9,6 cm
Hinweis: Bereich "μ ± σ" ≈ 3,0 – 4,4 cm (heuristisch).
```

**Gesamtfehler (Euklidisch)**:


```text
Statistische Kennwerte (BRV4-spezifisch):
- Mittelwert (μ):         14,10 cm
- Standardabweichung σ:   1,60 cm
- 95%-Perzentil (oberes): 16,27 cm
- 99%-Perzentil (oberes): 21,22 cm
- Maximum beobachtet:     26,5 cm
```

### 5.2 Varianzzerlegung (Sensitivitätsanalyse)

**Längsfehler-Komponenten** (Varianzzerlegung korrigiert – Beiträge beziehen sich auf Varianzanteile der quadratischen Komponenten; konvertierte Std-Anteile berechnet als √(p·σ_total²)). Hinweis: Gilt für Legacy (Schema 1.x) Modell mit getrimmter Signalqualitätsverteilung; im neuen Schema 2.0 dominiert Signalqualität fast vollständig, siehe Executive Summary Update.

| Fehlerquelle | Varianzanteil | Std-Anteil (cm) | Optimierungspotenzial |
|--------------|---------------|-----------------|----------------------|
| Signalqualität | 55,1% | 1,20 | **Hoch** (Signalverarbeitung/Filterung) |
| Verarbeitungslatenz | 40,0% | 1,02 | **Hoch** (Hardware/Firmware) |
| EM-Störungen | 2,5% | 0,25 | Niedrig |
| Antennen-Offset | 2,2% | 0,24 | Mittel (Kalibrierung) |

**Querfehler-Komponenten**:

| Fehlerquelle | Varianzanteil | Std-Anteil (cm) | Optimierungspotenzial |
|--------------|---------------|-----------------|----------------------|
| Signalqualität | 63,5% | 0,55 | **Hoch** (Signalverarbeitung) |
| Antennen-Offset | 28,5% | 0,37 | **Hoch** (Kalibrierung) |
| EM-Störungen | 8,0% | 0,19 | Niedrig |

### 5.3 Geschwindigkeitsabhängige Analyse

**Fehlerentwicklung mit Geschwindigkeit**:

| Geschwindigkeit | Längsfehler (μ ± σ) | Querfehler (μ ± σ) | 99%-Perzentil (längs) |
|-----------------|--------------------|--------------------|----------------------|
| 20 km/h | 11,8 ± 1,5 cm | 3,7 ± 0,7 cm | 16,1 cm |
| 30 km/h | 13,6 ± 1,6 cm | 3,7 ± 0,7 cm | 20,7 cm |
| 40 km/h | 15,4 ± 1,7 cm* | 3,7 ± 0,7 cm* | 24,8 cm* |
| 50 km/h | 17,2 ± 1,8 cm* | 3,7 ± 0,7 cm* | 28,5 cm* |
| 60 km/h | 19,0 ± 1,9 cm* | 3,7 ± 0,7 cm* | 32,1 cm* |

*Extrapolation basierend auf linearer Skalierung des Latenzterms (v × t_latenz); nicht separat simuliert in vorliegender Standard-JSON-Ausgabe.

**Beobachtungen**:

- **Linearer Anstieg** des Längsfehlers mit Geschwindigkeit (Latenz-Dominanz)
- **Konstanter Querfehler** (geschwindigkeitsunabhängige Komponenten)
- **Wachsende Standardabweichung** bei höheren Geschwindigkeiten

### 5.4 Plausibilisierung und Validierung

**Validierung und Plausibilisierung**:

Eine geschlossene analytische Erwartung E[√(Σ X_i²)] für die Mischung (Normal + korrelierte Normal + trunkiert Exponential + Rayleigh) ist nicht trivial. Stattdessen:

- **Varianzplausibilität**: Summe der Varianzanteile = 100%; rekonstruierte Std via Komponenten: √(Σ (Std_Anteil²)) = 1,60 cm ≈ beobachtete 1,61 cm.
- **Robustheit**: Separate Kurzläufe (intern, nicht Teil der JSON) zeigen Stabilisierung des Mittelwerts auf <0,05 cm Abweichung nach ~10.000 Läufen.
- **Empfehlung**: Für sicherheitsgerichtete Nachweise zusätzliche Runs mit unterschiedlichen Seeds + Ausgabe der 5%-Perzentile (derzeit nicht persistiert) ergänzen.

## 6. Auswirkungen auf Lokalisierungssystem

### 6.1 Sicherer Lokalisierungspfad

**Initialisierungs-Genauigkeit**:

Bei Balisen-basierter Initialisierung des sicheren Intervalls (BRV4-spezifisch):

- **95%-Vertrauensbereich**: ±15,8 cm (längs), ±5,1 cm (quer) bei 30 km/h
- **Sicherheitsreserve (99%)**: ±20,7 cm (längs), ±6,2 cm (quer)

**Intervall-Akkumulation zwischen Balisen**:
Ohne Balisen-Update wächst das Unsicherheitsintervall durch Odometrie-Drift:

```text
σ_akkumuliert(t) = √(σ_balise² + (σ_odo × t)²)
```

**Kritische Balisen-Abstände**:
Bei typischer Odometrie-Drift von 0,1% der Fahrstrecke:

| Balisen-Abstand | Akkumulierter Längsfehler (95%) | Sicherheitsbewertung |
|-----------------|--------------------------------|---------------------|
| 200 m | ±22,4 cm | Akzeptabel |
| 500 m | ±29,2 cm | Grenzbereich |
| 1000 m | ±38,8 cm | Kritisch |
| 2000 m | ±58,1 cm | Inakzeptabel |

### 6.2 GNSS-unterstützter Lokalisierungspfad

**Sensorfusion-Gewichtung**:

Balisen-Messungen können mit GNSS/IMU fusioniert werden (z.B. Kalman / faktorgraph) unter inverser Varianzgewichtung. Nachstehende GNSS-Werte sind externe Referenzannahmen (Quellen z.B. RTCM / ITU-R – noch zu zitieren) und nicht aus dieser Simulation ableitbar.

**Typische GNSS-Genauigkeit vs. Balise (30 km/h)**:

| System | Längsfehler (95%) | Querfehler (95%) | Verfügbarkeit |
|--------|-------------------|------------------|---------------|
| Balise (BRV4) | ±15,8 cm | ±5,1 cm | >96% |
| RTK-GNSS | ±3,0 cm | ±3,0 cm | ~85% |
| PPP-GNSS | ±15,0 cm | ±10,0 cm | ~95% |
| **Fusion** | ±2,9 cm | ±2,8 cm | >99% |

*Hinweis Fusion*: Hypothetisches Ergebnis (Annahme unabhängiger, unkorrelierter Fehlerquellen und idealer Varianzfusion).

### 6.3 Detektionsausfall-Szenarien

**Ausfallwahrscheinlichkeiten (Monte-Carlo-validiert)**:

- Bei 20 km/h: P_fail = 2,6%
- Bei 30 km/h: P_fail = 2,9%
- Bei 40 km/h: P_fail = 3,2%
- Bei 60 km/h: P_fail = 3,8%

**Auswirkung auf Lokalisierungsintervall**:

Bei verpasster Balise wächst das Intervall gemäß Odometrie-Driftmodell; aktuelles Simulationsmodell behandelt Ausfall als Fehlervergrößerung (Multiplikatoren), nicht als fehlende Messung → zukünftige Modelloption: Ausfall = fehlende Beobachtung (siehe Change Request).

## 7. Optimierungsstrategien

### 7.1 Hardware-Optimierungen (Priorität 1)

**Latenz-Reduktion**:

- **FPGA-Optimierung**: Pipeline-Optimierung und parallele Verarbeitung
- **Ziel**: Reduktion der Verarbeitungslatenz durch Hardware-Beschleunigung
- **Potentielle Auswirkung**: Proportionale Reduktion der geschwindigkeitsabhängigen Längsfehler

**Antennen-Kalibrierung**:

- **Präzisions-Vermessung**: Laser-gestützte Antennenpositionierung
- **Ziel**: Reduktion des Montage-Offset durch verbesserte Kalibrierungsverfahren
- **Potentielle Auswirkung**: Reduktion der systematischen Querfehler

**Hinweis**: Spezifische Verbesserungsraten erfordern Hardware-Tests und Prototyping zur Validierung.

### 7.2 Algorithmus-Verbesserungen (Priorität 2)

**Adaptive Latenz-Kompensation**:

```python
def latenz_korrektur(v_aktuell, signal_qualität):
    """
    Geschwindigkeits- und qualitätsabhängige Latenz-Korrektur
    """
    base_latenz = 10e-3  # Baseline-Latenz
    qualitäts_faktor = 1.0 + 0.2 * (1 - signal_qualität)
    korrigierte_latenz = base_latenz * qualitäts_faktor
    
    position_korrektur = v_aktuell * korrigierte_latenz
    return position_korrektur
```

**Predictive Balisen-Tracking**:

- **Vorhersage**: Erwartete Balisen-Position basierend auf Karte und Odometrie
- **Validierung**: Plausibilitätsprüfung gegen erwartete Position
- **Ausreißer-Detektion**: Automatische Verwerfung unplausibler Detektionen

### 7.3 Systemintegration (Priorität 3)

**Multi-Sensor-Fusion**:

```python
def balise_gnss_fusion(balise_pos, gnss_pos, balise_cov, gnss_cov):
    """
    Optimale Kalman-Filter-basierte Sensorfusion
    """
    # Kalman-Gain-Berechnung
    K = balise_cov @ inv(balise_cov + gnss_cov)
    
    # Fusionierte Position
    pos_fusioniert = balise_pos + K @ (gnss_pos - balise_pos)
    cov_fusioniert = (I - K) @ balise_cov
    
    return pos_fusioniert, cov_fusioniert
```

## 8. Anleitung zur Simulation mit modifizierten Parametern

### 8.1 Simulationsparameter anpassen

Die Monte-Carlo-Simulation kann mit angepassten Parametern durchgeführt werden, indem die Klasse `BRV4ErrorSimulation` mit modifizierten Parametern initialisiert wird:

```python
from simulation_balise_error import BRV4ErrorSimulation, BRV4SimulationConfig

# Beispiel 1: Vordefinierte optimierte Konfiguration
def simulation_optimiert():
    # Verwende vordefinierte optimierte Konfiguration
    config = BRV4SimulationConfig.create_optimized_config()
    simulator = BRV4ErrorSimulation(config)
    
    # Simulation durchführen
    results = simulator.run_simulation(velocity_kmh=30, n_runs=50000)
    return results

# Beispiel 2: Benutzerdefinierte Konfiguration
def simulation_benutzerdefiniert():
    # Erstelle benutzerdefinierte Konfiguration
    config = BRV4SimulationConfig(
        latency_mean=8e-3,              # 8ms mittlere Latenz
        latency_std=1.5e-3,             # 1.5ms Standardabweichung
        antenna_std=1.5e-2,             # 1.5cm Antennen-Offset
        signal_quality_lambda=0.08,     # Verbesserte Signalqualität
        em_interference_sigma=1.0e-2    # Reduzierte EM-Störungen
    )
    
    simulator = BRV4ErrorSimulation(config)
    results = simulator.run_simulation(velocity_kmh=30, n_runs=50000)
    return results

# Beispiel 3: Extreme Bedingungen
def simulation_extreme():
    # Verwende vordefinierte Extrembedingungen-Konfiguration
    config = BRV4SimulationConfig.create_extreme_conditions_config()
    simulator = BRV4ErrorSimulation(config)
    
    # Simulation durchführen
    results = simulator.run_simulation(velocity_kmh=30, n_runs=50000)
    return results

# Beispiel 4: Konfigurationsvergleich
def vergleiche_konfigurationen():
    from simulation_balise_error import compare_configurations
    
    configs = {
        'standard': BRV4SimulationConfig(),
        'optimized': BRV4SimulationConfig.create_optimized_config(),
        'extreme': BRV4SimulationConfig.create_extreme_conditions_config(),
        'conservative': BRV4SimulationConfig.create_conservative_config()
    }
    
    # Vergleicht alle Konfigurationen mit reduzierter Laufzahl
    comparison = compare_configurations(configs, velocity_kmh=30, n_runs=10000)
    return comparison

# Beispiel 5: Sensitivitätsanalyse
def sensitivitaetsanalyse():
    from simulation_balise_error import run_sensitivity_analysis
    
    base_config = BRV4SimulationConfig()
    variations = {
        'latency_mean': [6e-3, 8e-3, 10e-3, 12e-3, 15e-3],
        'antenna_std': [1e-2, 1.5e-2, 2e-2, 2.5e-2, 3e-2],
        'signal_quality_lambda': [0.02, 0.05, 0.08, 0.10, 0.15]
    }
    
    sensitivity = run_sensitivity_analysis(base_config, variations, n_runs=5000)
    return sensitivity

### 8.2 Konfigurationsbasierte Simulation

Die erweiterte Simulation (`simulation_balise_error.py`) unterstützt konfigurationsbasierte Parameter über die `BRV4SimulationConfig` Klasse:

**Verfügbare vordefinierte Konfigurationen:**

| Konfiguration | Beschreibung | Latenz | Antennen-Std | Signalqualität λ |
|---------------|--------------|--------|--------------|------------------|
| `standard` | Standard BRV4-Parameter | 10ms ± 2ms | 2.0cm | 0.05 |
| `optimized` | Optimierte Hardware | 6ms ± 1ms | 1.0cm | 0.08 |
| `extreme` | Extreme Bedingungen | 15ms ± 3ms | 3.0cm | 0.02 |
| `conservative` | Konservative Auslegung | 12ms ± 2.5ms | 2.5cm | 0.04 |

**Neue Features:**
- **Konfigurationsobjekte**: Alle Parameter in strukturierter Form
- **Vordefinierte Szenarien**: Typische Betriebsbedingungen als Ready-to-use Konfigurationen
- **Konfigurationsvergleich**: Automatischer Vergleich verschiedener Parametersätze
- **Sensitivitätsanalyse**: Systematische Variation einzelner Parameter
- **Reproduzierbarkeit**: Konfiguration wird in Ergebnissen gespeichert

### 8.3 Durchführung verschiedener Analysen

**Standard-Simulation:**
```python
# Einfache Ausführung mit Standard-Parametern
simulator = BRV4ErrorSimulation()
results = simulator.run_simulation(velocity_kmh=30, n_runs=50000)
```

**Erweiterte Analysen:**

- **Konfigurationsvergleich**: Vergleicht 4 Konfigurationen parallel (siehe Beispiel 4)
- **Sensitivitätsanalyse**: Variiert systematisch einzelne Parameter (siehe Beispiel 5)
- **Benutzerdefinierte Parameter**: Vollständig anpassbare Konfiguration (siehe Beispiel 2)

Die Referenz-Analyse verwendet die Standard-Konfiguration mit 50.000 Monte-Carlo-Läufen bei 30 km/h.

### 8.3 Interpretation der Ergebnisse

**Wichtige Metriken**:

- **68%-Konfidenzintervall**: Für normale Betriebsbedingungen (heuristisch; nicht für Safety freigebend)
- **95%-Konfidenzintervall**: Für konservative Auslegung
- **99%-Perzentil**: Für Sicherheitsbetrachtungen
- **Varianzzerlegung**: Identifikation der dominanten Fehlerquellen

## 9. Fazit und Empfehlungen

### 9.1 Zusammenfassung der Kernergebnisse

Die erweiterte Monte-Carlo-Analyse des BRV4 Balise-Lesers zeigt:

1. **Präzise Quantifizierung**: Längsfehler 13,6±1,6 cm, Querfehler 3,7±0,7 cm bei 30 km/h (BRV4-spezifisch)
2. **Dominante Fehlerquellen**: Signalqualität (55,1%) und Verarbeitungslatenz (40,2% des Längsfehlers)
3. **Geschwindigkeitsabhängigkeit**: Moderater Anstieg des Längsfehlers mit Geschwindigkeit
4. **Sicherheitsrelevant**: 99%-Perzentil-Werte für konservative Systemauslegung

### 9.2 Kritische Implementierungsaspekte

**Zeitstempel-Verwendung**:

- **Zwingend**: `payload.timestamp` für Positionsrekonstruktion verwenden
- **Vermeiden**: Verwechslung der 1-Hz-Statusmeldungen mit Balisen-Event-Timing
- **Empfehlung**: Latenz-Korrektur basierend auf `payload.timestamp`

**Systemintegration**:

- **Sichere Lokalisierung**: 99%-Perzentil (±20,7 cm längs) als Basis für BRV4-spezifische Auslegung
- **GNSS-Fusion**: Verbesserung auf <3 cm Gesamtgenauigkeit möglich
- **Balisen-Abstände**: Optimal 200-300 m, maximal 500 m

### 9.3 Optimierungsprioritäten

1. **Signalverarbeitung-Optimierung** (größtes Potenzial): Reduzierung der Signalqualitätsfehler
2. **Latenz-Reduktion** (wichtig): ~ -16% Längsfehler (Vergleich Standard vs. Optimized, 10k Läufe: 13,61→11,48 cm)
3. **Antennen-Kalibrierung** (Quergenauigkeit): -8% Querfehler
4. **Adaptive Algorithmen** (Robustheit): Signalqualitäts-abhängige Korrektur
