import datetime
import os.path
import re

import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config_manager import ConfigManager

# Stałe

# Zakresy dostępu dla Google Calendar API
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Tabela miesięcy, wspiera różne formaty nazw (polskie i angielskie)
MONTHS_MAP = {
    "01": 1, "1": 1, "styczeń": 1, "styczen": 1, "january": 1, "jan": 1,
    "02": 2, "2": 2, "luty": 2, "february": 2, "feb": 2,
    "03": 3, "3": 3, "marzec": 3, "march": 3, "mar": 3,
    "04": 4, "4": 4, "kwiecień": 4, "kwiecien": 4, "april": 4, "apr": 4,
    "05": 5, "5": 5, "maj": 5, "may": 5,
    "06": 6, "6": 6, "czerwiec": 6, "june": 6, "jun": 6,
    "07": 7, "7": 7, "lipiec": 7, "july": 7, "jul": 7,
    "08": 8, "8": 8, "sierpień": 8, "sierpien": 8, "august": 8, "aug": 8,
    "09": 9, "9": 9, "wrzesień": 9, "wrzesien": 9, "september": 9, "sep": 9,
    "10": 10, "październik": 10, "pazdziernik": 10, "october": 10, "oct": 10,
    "11": 11, "listopad": 11, "november": 11, "nov": 11,
    "12": 12, "grudzień": 12, "grudzien": 12, "december": 12, "dec": 12,
}

# Funkcje API
def authenticate_google_calendar():
    """
    Uwierzytelnienie użytkownika dla Google Calendar API.
    """
    creds = None

    # Sprawdzenie, czy plik z tokenem istnieje
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # Ponowne uwierzytelnienie w razie potrzeby
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def parse_shift_input(input_string, default_duration, default_shift):
    """
    Przetwarza wejściowy tekst z danymi dotyczącymi zmian i zwraca listę zmian.
    """
    pattern = re.compile(r"(\d{1,2})([DN]?)\s*(\d{1,2}h)?(\d{1,2}m)?")
    shifts = []

    for match in pattern.finditer(input_string):
        day = int(match.group(1))
        shift_type = match.group(2) if match.group(2) else default_shift
        hours = int(match.group(3)[:-1]) * 60 if match.group(3) else 0
        minutes = int(match.group(4)[:-1]) if match.group(4) else 0
        duration = hours + minutes if hours or minutes else default_duration
        shifts.append({"day": day, "shift_type": shift_type, "duration": duration})

    return shifts


def check_existing_event(service, calendar_id, start_time, shift_duration):
    """
    Sprawdza, czy w Google Calendar istnieje wydarzenie w podanym czasie.
    """
    warsaw_tz = pytz.timezone("Europe/Warsaw")
    start_time_local = warsaw_tz.localize(start_time, is_dst=None)
    end_time_local = start_time_local + datetime.timedelta(minutes=shift_duration)

    time_min = start_time_local.astimezone(pytz.utc).isoformat()
    time_max = end_time_local.astimezone(pytz.utc).isoformat()

    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        return bool(events)
    except HttpError as error:
        print(f"Błąd podczas sprawdzania wydarzeń: {error}")
        return False


def create_summary(shifts, month, hourly_rate):
    """
    Generuje podsumowanie przepracowanego czasu i zarobków.
    """

    total_day_minutes = 0
    total_weekend_minutes = 0
    total_night_minutes = 0

    for shift in shifts:
        shift_date = datetime.date(datetime.date.today().year, month, shift["day"])
        is_weekend = shift_date.weekday() >= 5  # Sobota (5), Niedziela (6)

        if is_weekend:
            total_weekend_minutes += shift['duration']
        else:
            total_day_minutes += shift["duration"]


    #     TODO:
    #     - calculate night hours


    total_minutes = total_day_minutes + total_weekend_minutes + total_night_minutes
    total_earnings = (total_day_minutes / 60 * hourly_rate) + \
                     (total_weekend_minutes / 60 * hourly_rate * 1.65) + \
                     (total_night_minutes / 60 * hourly_rate * 1.65)
    total_hours = total_minutes / 60

    # Wyświetlenie podsumowania
    print("\n=== Podsumowanie czasu pracy ===")
    print(f"Godziny dzienne: {total_day_minutes // 60}h {total_day_minutes % 60}m")
    print(f"Godziny weekendowe: {total_weekend_minutes // 60}h {total_weekend_minutes % 60}m")
    print(f"Łącznie godzin: {int(total_hours)}h {total_day_minutes % 60}m")
    print(f"Zarobki: {total_earnings:.2f} zł")


def create_calendar_events(service, shifts: list[dict], calendar_id: str, month: int, day_start: dict[str, int],
                           night_start: dict[str, int], default_duration: int, hourly_rate: float
):
    """
    Dodaje wydarzenia zmian do Google Calendar.
    """
    
    today = datetime.date.today()
    year, month = today.year, month
    for shift in shifts:
        if shift["shift_type"] == "D":
            start_hour, start_minute = day_start["hour"], day_start["minute"]
        else:
            start_hour, start_minute = night_start["hour"], night_start["minute"]

        start_time = datetime.datetime(year, month, shift["day"], start_hour, start_minute)
        end_time = start_time + datetime.timedelta(minutes=shift.get("duration", default_duration))

        # Sprawdzamy, czy w tym samym czasie już istnieje wydarzenie
        if check_existing_event(service, calendar_id, start_time, default_duration):
            print(f"Zmiana na {start_time} już istnieje. Pomijam dodanie.")
            continue  # Przechodzimy do kolejnej zmiany

        # Tworzymy wydarzenie do dodania do Google Calendar
        event = {
            "summary": f"{shift['shift_type']}",
            "description": f"{'Dzienna' if shift['shift_type'] == 'D' else 'Nocna'} zmiana ({int(shift['duration'] / 60)}h)",
            "start": {"dateTime": start_time.isoformat(), "timeZone": "Europe/Warsaw"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "Europe/Warsaw"},
        }

        # Dodanie wydarzenia do Google Calendar
        service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Dodano zmianę: {event['summary']} ({event['description']}) - {start_time} -> {end_time}")
    create_summary(shifts, month, hourly_rate)


def get_next_month():
    """
    Zwraca liczbę odpowiadającą następnemu miesiącowi.
    """
    today = datetime.date.today()
    return today.month + 1 if today.month < 12 else 1

def select_month():
    """
    Umożliwia wybór miesiąca z wykorzystaniem domyślnego ustawienia.
    """
    default_month = get_next_month()

    while True:
        user_input = input(f"Wybierz miesiąc (domyślnie {datetime.date(2025, get_next_month(), 1)
                           .strftime('%B')}): ").strip().lower()
        if not user_input:
            return default_month
        if user_input in MONTHS_MAP:
            return MONTHS_MAP[user_input]
        print("Niepoprawny wybór, spróbuj ponownie.")


def main():
    """
    Główna funkcja programu
    """
    settings = ConfigManager.ensure_settings()
    calendar_id = settings["calendar_id"]

    service = authenticate_google_calendar()
    selected_month = select_month()
    
    default_duration = settings["default_shift_duration"]["total_minutes"]
    default_shift = settings["default_shift"]
    shift_start = settings["shift_start"]
    hourly_rate = float(settings["hourly_rate"])

    user_input = input("Podaj dni pracy (np. 12, 13 8h, 1N, 4 6h30m): ").strip()
    shifts = parse_shift_input(user_input, default_duration, default_shift)

    if shifts:
        day_shift_start = shift_start["day"]
        night_shift_start = shift_start["night"]
        create_calendar_events(service, shifts, calendar_id, selected_month, day_shift_start, night_shift_start,
                               default_duration, hourly_rate)
    else:
        print("Nie podano zmian.")


if __name__ == "__main__":
    main()