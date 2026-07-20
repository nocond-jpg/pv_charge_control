# PV Charge Control

Integracja Home Assistant sterująca natężeniem ładowania EV na podstawie **nadwyżki produkcji PV**, minimalizująca rozładowanie magazynu energii.

## Co robi

Co kilka–kilkanaście sekund odczytuje SoC magazynu, moc PV, zużycie domu i moc baterii, liczy realną nadwyżkę i ustawia natężenie na jednej lub dwóch ładowarkach. Celuje w ładowanie **tylko z PV** — gdy magazyn się rozładowuje, nadwyżka jest odpowiednio pomniejszana.

## Instalacja (HACS)

1. HACS → Integrations → menu (⋮) → **Custom repositories**
2. URL repozytorium, kategoria **Integration**
3. Zainstaluj **PV Charge Control**, zrestartuj HA
4. Ustawienia → Urządzenia i usługi → **Dodaj integrację** → PV Charge Control

## Konfiguracja (UI)

Podczas dodawania wskazujesz encje:

| Pole | Typ | Wymagane |
|------|-----|----------|
| SoC magazynu (%) | sensor | tak |
| Moc PV (W) | sensor | tak |
| Zużycie domu (W) | sensor | tak |
| Moc baterii (W) | sensor | tak |
| Ładowarka główna (6–16 A) | number | tak |
| Ładowarka druga (3–16 A) | number | nie |
| Blokada z auta | switch | nie |
| Blokada z ładowarki | switch | nie |

Parametry (min SoC, napięcie, fazy, histereza, interwał, znak mocy baterii) zmienisz w **Konfiguruj** integracji.

## Sterowanie

- Włącznik **„Sterowanie ładowaniem PV"** (switch) uruchamia/wyłącza logikę. Po wyłączeniu prąd jest zerowany.
- Ładowarki: gdy potrzebny prąd < 6 A, główna = 0; druga może startować od 3 A. Priorytet ma główna, nadmiar idzie na drugą.
- Encje `number` niedostępne / `unavailable` są pomijane (druga ładowarka bywa niedostępna — obsłużone).
- Przełączniki blokady w stanie `on` zerują ładowanie; gdy `unavailable` — nie blokują.

## Logika nadwyżki

`nadwyżka = PV − zużycie_domu(bez auta)`. Jeśli magazyn się rozładowuje, odejmowana jest jego moc (nie „pożyczamy" z baterii). Poniżej `min SoC` ładowanie jest wstrzymane. Histereza tworzy martwą strefę zapobiegającą oscylacjom.

> **Uwaga o znaku mocy baterii:** różne inwertery raportują ładowanie jako dodatnie lub ujemne. Jeśli zachowanie jest odwrotne — zaznacz *Odwróć znak mocy baterii* w opcjach.

## Encje diagnostyczne

Nadwyżka PV (W), Prąd ładowarki głównej/drugiej (A), Status decyzji.

## Status

**POC** — przetestuj na swojej instalacji i dostrój histerezę/interwał.
