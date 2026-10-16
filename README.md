# IEC61850 Reader für Windows

Lokaler IEC-61850/MMS-Client mit grafischer Oberfläche. Die native
Protokollschicht verwendet die offizielle Open-Source-Bibliothek
`libiec61850` 1.6.2 von MZ Automation.

## Funktionen der ersten Version

- MMS-Verbindungsprüfung über TCP, Standardport 102
- automatisches Online-Browsing von Logical Devices, Logical Nodes,
  Data Objects und Data Attributes
- Anzeige gefundener URCBs und BRCBs
- dauerhaftes Aktivieren und Empfangen von URCB-/BRCB-Reports
- GOOSE-Mitschnitt über einen auswählbaren Npcap-Netzwerkadapter
- TLS-Verbindungen nach IEC 62351-3/4 mit lokaler CA, Clientzertifikat und Schlüssel
- durchsuchbarer Modellbaum
- Werte mit auswählbarem Functional Constraint lesen
- boolesche, vorzeichenbehaftete, vorzeichenlose, Gleitkomma- und
  sichtbare Stringwerte schreiben
- Control-Objekte auswählen, ausführen und abbrechen
- Origin-Kategorie, Test, Interlock- und Synchro-Prüfung
- lokaler Import von ICD-, CID-, SCD- und IID-Dateien
- Werteliste, Ereignisprotokoll und CSV-Export
- keine Cloud-Dienste und keine Telemetrie

## Bedienung

1. IP-Adresse und TCP-Port des IED eintragen.
2. **Verbindung prüfen** auswählen.
3. Mit **Online-Modell lesen** das vom IED bereitgestellte Modell laden.
4. Ein Datenattribut doppelt anklicken oder **Senden ...** öffnen.
5. Beim Lesen den zum Attribut passenden Functional Constraint auswählen,
   beispielsweise `MX` für Messwerte oder `ST` für Statuswerte.

Schreiben und Steuern erfordern eine ausdrückliche Bestätigung. Die Anwendung
kann nicht beurteilen, ob eine Objektreferenz gefahrlos geschaltet werden darf.
Control Model, Datentyp, Origin-Kategorie und Prüfoptionen müssen mit der
Hersteller- und Anlagenkonfiguration übereinstimmen.

## SCL-Import

Der Import liest die Grundstruktur von IED, Logical Devices und Logical Nodes
lokal aus XML-basierten SCL-Dateien. Die Datei wird nicht verändert oder an
einen externen Dienst gesendet. Das Online-Modell bleibt für die tatsächlich
vom Gerät angebotenen Daten maßgeblich.

## Reports, GOOSE und TLS

Der Dialog **Reports / GOOSE / TLS ...** startet ein dauerhaftes
Report-Abonnement oder einen GOOSE-Empfänger als getrennten Hintergrundprozess.
Beim Schließen des Dialogs werden diese Monitore kontrolliert beendet. Für ein
Report-Abonnement müssen RCB- und DataSet-Referenz exakt zur IED-Konfiguration
passen.

GOOSE erfordert eine installierte Npcap-Laufzeit im WinPcap-kompatiblen Modus
und die passende Npcap-Adapter-ID. Der Build verwendet nur das Npcap SDK; der
Treiber selbst wird nicht mitgeliefert oder automatisch installiert.

TLS wird nur aktiviert, wenn CA-Zertifikat, Clientzertifikat und privater
Schlüssel lokal ausgewählt wurden. Die Zertifikatsprüfung und die Beschränkung
auf bekannte Zertifikate sind aktiviert. Geheimnisse werden nicht im Programm
oder in der Konfiguration hinterlegt.

## Verbleibende Grenzen

- Jede Aktion baut derzeit eine eigene MMS-Verbindung auf. Das ist robust für
  Diagnosezwecke, aber noch kein dauerhaft verbundener Leitstellenclient.

## Build

Der GitHub-Workflow lädt libiec61850 1.6.2.1 aus dem offiziellen Repository,
kompiliert die native Windows-Brücke mit CMake und packt sie zusammen mit der
Python/Tk-Oberfläche in eine portable `IEC61850-Reader.exe`.

## Lizenz

GPLv3. Die eingebundene libiec61850-Bibliothek steht ebenfalls unter GPLv3.
