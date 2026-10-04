# iCloud Calendar MCP Server

Lokalny serwer MCP do obsługi kalendarzy iCloud przez CalDAV. Działa przez stdio na Windows, macOS i Linux.

## Wymagania

- Python 3.12 lub nowszy.
- Konto Apple z uwierzytelnianiem dwuskładnikowym.
- Hasło aplikacji utworzone na [account.apple.com](https://account.apple.com/) w sekcji **Logowanie i zabezpieczenia → Hasła aplikacji**. Nie używaj głównego hasła konta.

## Instalacja

1. Sklonuj repozytorium: `git clone https://github.com/ycangignacy/icloudmcpserver.git` i przejdź do katalogu `icloudmcpserver`.
2. Utwórz środowisko i zainstaluj zależności:

   Windows (PowerShell):

   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Copy-Item .env.example .env.local
   ```

   macOS / Linux:

   ```sh
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   cp .env.example .env.local
   ```

3. Wpisz swój adres konta Apple i hasło aplikacji do `.env.local`. `APPLE_CALDAV_URL` zwykle nie wymaga zmiany.

## Podłączenie do klienta MCP

Dodaj serwer typu stdio w konfiguracji klienta MCP. Ustaw pełną ścieżkę do Pythona w `.venv` jako polecenie oraz pełną ścieżkę do `server.py` jako argument. Przykład dla klienta używającego JSON:

```json
{
  "mcpServers": {
    "icloud-calendar": {
      "command": "/pełna/ścieżka/do/icloudmcpserver/.venv/bin/python",
      "args": ["/pełna/ścieżka/do/icloudmcpserver/server.py"]
    }
  }
}
```

Na Windows w `command` użyj `.venv\Scripts\python.exe`; ścieżki w JSON zapisz z podwójnymi ukośnikami odwrotnymi. Format konfiguracji zależy od klienta MCP. Serwer sam odczytuje `.env.local` z katalogu `server.py`, więc hasła nie trzeba wpisywać w konfiguracji klienta. Po podłączeniu wywołaj `list_calendars`, aby uzyskać ID kalendarzy.

Skrypt `start.ps1` pozwala uruchomić serwer na Windows z katalogu projektu. Proces oczekuje na komunikaty MCP na standardowym wejściu; brak tekstowego menu jest prawidłowy.

## Narzędzia

| Narzędzie | Działanie |
| --- | --- |
| `list_calendars` | Lista kalendarzy i ich identyfikatorów. |
| `list_events` | Wystąpienia wydarzeń w przedziale dat; koniec przedziału jest wyłączny. |
| `get_event` | Szczegóły wydarzenia i pełny ICS na podstawie UID. |
| `create_event` | Utworzenie wydarzenia. |
| `update_event` | Edycja głównego wydarzenia lub serii cyklicznej. |
| `delete_event` | Usunięcie wydarzenia lub całej serii. |

Daty całodniowe podawaj jako `YYYY-MM-DD`. Dla wydarzeń z godziną używaj ISO 8601 ze strefą, np. `2026-10-04T14:00:00+02:00`. Koniec wydarzenia całodniowego jest wyłączny: jednodniowe wydarzenie ma datę końca o dzień późniejszą niż data początku. Edycja serii cyklicznej zmienia jej główny komponent; istniejące wyjątki mogą zachować osobne godziny i opisy. Usunięcie po UID usuwa całą serię.

## Kopie i prywatność

Serwer zapisuje pełny ICS przed edycją i usunięciem wydarzenia oraz po utworzeniu i edycji w `kopie zapasowe/wydarzenia`. Pliki ICS mogą zawierać prywatne szczegóły spotkań. `.env.local`, kopie zapasowe i `.venv` są ignorowane przez Git. Nie przesyłaj ich do repozytorium.
