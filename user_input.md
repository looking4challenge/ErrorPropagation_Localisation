Ich prüfe die Implementierung in time_sim.py, um exakt zu verifizieren, wann der Modus unsafe_clamped gesetzt wird. 

Searched text for `unsafe_clamped` (`**/src/time_sim.py`), 5 results

Lese relevanten Abschnitt von time_sim.py um Logik für unsafe_clamped zu verstehen. 

Read [](file:///c%3A/Repos/ErrorPropagation_Localisation/src/time_sim.py)

Untersuche die Implementierung von rule_based_fusion_step in fusion.py um die Bedingung für unsafe_clamped exakt zu bestätigen. 

Searched text for `unsafe_clamped` (`**/src/fusion.py`), 15 results

Lese relevanten Abschnitt von fusion.py für die Entscheidungslogik. 

Read [](file:///c%3A/Repos/ErrorPropagation_Localisation/src/fusion.py)

Ja, fast – Du liegst richtig im Kern, aber lass mich die genaue Semantik präzise auseinanderziehen, damit der Plot eindeutig interpretierbar ist.

Kurzfassung
unsafe_clamped bedeutet (im Standard-Setup): Der unsichere (präzisere) Pfad (GNSS+IMU) ist verfügbar, liegt aber außerhalb des aktuell gültigen sicheren Intervalls, daher fällt die Fusion auf den sicheren Pfad zurück (und clamped ihn in die Intervallgrenzen). Der unsichere Wert selbst wird in diesem Modus nicht verwendet. Bei GNSS‑Outage (Ausfall) dagegen wird standardmäßig der Modus midpoint benutzt (nicht unsafe_clamped), außer man hätte outage_fallback=secure konfiguriert – dann würden auch Ausfälle als unsafe_clamped erscheinen.

Details anhand des Codes
1. Modus-Codierung (fusion.py):
   0 = midpoint  
   1 = unsafe  
   2 = unsafe_clamped  

2. Entscheidungslogik (rule_based_fusion_step):
   - unsafe (MODE_UNSAFE): unsafe ist verfügbar (kein Outage) UND liegt innerhalb [lower, upper].
   - midpoint (MODE_MIDPOINT): Outage und outage_fallback != "secure" (Default ist "midpoint").
   - unsafe_clamped (MODE_UNSAFE_CLAMPED):
     a) unsafe verfügbar aber außerhalb der Grenzen (|unsafe| > Intervall bzw. unsymmetrisch: unsafe < lower oder > upper) → Rückfall auf den sicheren Pfad, dieser wird auf [lower, upper] geclippt.
     b) (Nur falls so konfiguriert) Outage und outage_fallback == "secure" → gleiche Mode-Klasse, aber semantisch anderer Grund (kein Messwert statt Ausreißer).

3. Clamping:
   Für unsafe_clamped wird NICHT der unsichere Wert geclippt, sondern der secure Pfad (secure) genommen und anschließend geclippt:
   target[mode == MODE_UNSAFE_CLAMPED] = clip(secure, lower, upper)

4. Sicherer Intervallmittelpunkt (midpoint):
   midpoint = 0.5*(lower+upper). Bei symmetrischen Intervallen ist das 0, bei zukünftiger Asymmetrie nicht zwingend.

Interpretation des Plots fusion_mode_share.png
- Jede Fläche zeigt den Anteil der Samples pro Zeitschritt in einem Modus.
- Anteil unsafe = Wie oft der präzisere Pfad direkt genutzt werden konnte (innerhalb Grenzen).
- Anteil unsafe_clamped = (meist) wie oft der unsichere Pfad zwar da war, aber außerhalb lag (→ Sicherheitsgarantie greift, Rückfall auf sicheren Pfad). Falls dieser Anteil sehr hoch, kann das bedeuten:
  * Intervalle eventuell zu eng (zu aggressiv) oder
  * Unsicherer Pfad hat systematischen Bias / stärkere Varianz als angenommen.
- Anteil midpoint = Ausfälle (Outages) oder – bei späterer Asymmetrie – Rückgriff auf den Intervallmittelpunkt (derzeit primär Outages).

Wie prüfen ob Outages in unsafe_clamped geflossen sind?
Suche in Deiner Config (z.B. scenario_regular.yml) nach:
fusion:
  outage_fallback: secure
Wenn nicht gesetzt oder auf midpoint: Outages erscheinen im midpoint-Anteil, nicht in unsafe_clamped.

Empfehlung zur Klarstellung (optional)
Um Missverständnisse zu minimieren könntest Du:
- Den Modus unsafe_clamped in secure_fallback oder secure_clamped umbenennen.
- Einen separaten Modus für Outage-secure unterscheiden, falls outage_fallback=secure genutzt wird (z.B. outage_secure).

Schnelle sanity checks
- Wenn Du im Plot siehst, dass unsafe_clamped und midpoint zusammen >~80% sind, verliert der unsichere Pfad viel Wirkung → Intervalldesign oder Parametrisierung prüfen.
- Steigt unsichere Varianz (Var_unsafe(t)) stark an, erwartbar mehr unsafe_clamped.
- Bei breiter werdenden Intervallen (adaptive bins) sollte der unsafe-Anteil tendenziell wachsen (sofern kein struktureller Bias).

Fazit
Ja: unsafe_clamped = unsicherer Pfad außerhalb der sicheren Intervallgrenzen (Fallback auf sicheren, geclampter Wert), außer Du hast explizit outage_fallback=secure gesetzt – dann enthält dieser Modus auch Outages. Dein Verständnis ist somit korrekt, mit dieser kleinen Nuance.

Sag gern Bescheid, falls Du:
- Eine Kennzahl zur „Effizienz“ (Anteil wirklich genutzter unsicherer Präzisionspfad) extra ausgewiesen haben willst,
- Oder den Modus umbenennen / weiter differenzieren möchtest.

Soll ich Dir gleich einen Patch für eine klarere Modusbenennung oder eine zusätzliche Ausgabedatei (Mode-Zusammenfassung) vorbereiten? Just let me know.


Folgende Punkte in TODO.md aufnehmen:
Fehlermodell für unsicheren Pfad "IMU-Term (0.5 * bias * t^2) + GNSS-Bias/-Noise" liefert unverhälnissmässigen Drift. In Realität wird durch fusion in unsicherem Pfad(ekf mit IMU,GNSS). Ausserdem sind IMU Signale offset-kompensiert über einen Stillstandabgleich (offset=0, bei v=0km/h). Setze den Drift-Term Faktor auf statt 0.5 auf 0.001.
Ergänze jeden Plot mit einer kurzer Erklärung, Was ist es für Plot und was kann man daraus lesen(für Statistik Dummies). Plaziere diesen Text unterhalb von Titel in kleinerem, aber gut lesbaren Schrifft.