import json
import os
from datetime import datetime


class ConfigManager:
    SETTINGS_FILE = "settings.json"

    @staticmethod
    def load_settings():
        """Wczytuje ustawienia z pliku JSON."""
        if not os.path.exists(ConfigManager.SETTINGS_FILE):
            return {}
        with open(ConfigManager.SETTINGS_FILE, "r") as file:
            return json.load(file)

    @staticmethod
    def save_settings(settings):
        """Zapisuje ustawienia do pliku JSON."""
        with open(ConfigManager.SETTINGS_FILE, "w") as file:
            json.dump(settings, file, indent=4)

    @staticmethod
    def get_setting(key, default=None):
        """Pobiera pojedynczą wartość ustawienia."""
        settings = ConfigManager.load_settings()
        return settings.get(key, default)

    @staticmethod
    def set_setting(key, value):
        """Ustawia i zapisuje pojedynczą wartość ustawienia."""
        settings = ConfigManager.load_settings()
        settings[key] = value
        ConfigManager.save_settings(settings)

    @staticmethod
    def get_env_variable(key, default=None):
        """Pobiera wartość zmiennej środowiskowej."""
        return os.getenv(key, default)

    @staticmethod
    def ensure_settings():
        """Sprawdza, czy wymagane ustawienia istnieją, jeśli nie - pyta użytkownika."""
        settings = ConfigManager.load_settings()
        updated = False  # Flaga oznaczająca, czy trzeba zapisać plik

        if "calendar_id" not in settings or not settings["calendar_id"]:
            while True:
                calendar_id = input("Podaj Calendar ID: ").strip()
                if calendar_id:
                    settings["calendar_id"] = calendar_id
                    updated = True
                    break
                print("Calendar ID nie może być puste!")

        if "default_shift_duration" not in settings or not isinstance(settings["default_shift_duration"], dict):
            while True:
                default_shift_duration = input("Podaj ile trwa domyślna zmiana (format HH:MM, np. 12:30): ").strip()
                try:
                    shift_duration_parts = list(map(int, default_shift_duration.split(":")))
                    if len(shift_duration_parts) == 2:  # Format HH:MM
                        hours, minutes = shift_duration_parts
                        if 0 <= minutes < 60 and hours >= 0:
                            settings["default_shift_duration"] = {
                                "hours": hours,
                                "minutes": minutes,
                                "total_minutes": hours * 60 + minutes
                            }
                            updated = True
                            break
                    print("Wprowadź poprawny czas w formacie HH:MM, np. 12:30!")
                except ValueError:
                    print("Wprowadź poprawny czas w formacie HH:MM, np. 12:30!")

        # Lista akceptowanych wartości dla zmiany dziennej i nocnej
        shift_mapping = {
            "D": ["D", "Day", "Dzień", "Dniówka"],
            "N": ["N", "Night", "Noc", "Nocka"]
        }

        if "default_shift" not in settings or settings["default_shift"] not in shift_mapping:
            while True:
                default_shift = input(
                    "Domyślna zmiana ma być dzienna czy nocna? (D/N lub pełne nazwy): ").strip().capitalize()

                # Sprawdzanie, czy wpis pasuje do jednej z grup
                for key, values in shift_mapping.items():
                    if default_shift in values:
                        settings["default_shift"] = key  # Zapisujemy tylko "D" lub "N"
                        updated = True
                        break
                else:
                    print("Wpisz 'D' (Day, Dzień, Dniówka) lub 'N' (Night, Noc, Nocka).")

                if updated:
                    break

        yes_no_mapping = {
            "T": ["T", "Tak", "Yes", "Y"],
            "N": ["N", "Nie", "No"]
        }

        # Sprawdzanie ustawień godziny rozpoczęcia zmiany
        if "shift_start" not in settings or not isinstance(settings["shift_start"], dict):
            settings["shift_start"] = {"day": {}, "night": {}}

            while True:
                shift_start_day = input("Podaj o której zaczyna się zmiana dzienna (format HH:MM, np. 07:00): ").strip()
                try:
                    shift_start_time = datetime.strptime(shift_start_day, "%H:%M").time()
                    settings["shift_start"]["day"] = {"hour": shift_start_time.hour, "minute": shift_start_time.minute}
                    updated = True
                    break
                except ValueError:
                    print("Wprowadź poprawny format godziny (HH:MM)!")

            while True:
                shift_start_night = input("Podaj o której zaczyna się zmiana nocna (format HH:MM, np. 19:00): ").strip()
                try:
                    shift_start_time = datetime.strptime(shift_start_night, "%H:%M").time()
                    settings["shift_start"]["night"] = {"hour": shift_start_time.hour,
                                                        "minute": shift_start_time.minute}
                    updated = True
                    break
                except ValueError:
                    print("Wprowadź poprawny format godziny (HH:MM)!")

        if "hourly_rate" not in settings or not settings["hourly_rate"]:
            while True:
                hourly_rate = input("Podaj zarobki godzinowe brutto: ").strip()
                settings["hourly_rate"] = hourly_rate
                updated = True
                break

        if updated:
            ConfigManager.save_settings(settings)

        return settings


# Przykładowe użycie
if __name__ == "__main__":
    settings = ConfigManager.ensure_settings()
    print("Calendar ID:", ConfigManager.get_setting("calendar_id"))
    print("Google API Key:", ConfigManager.get_env_variable("GOOGLE_API_KEY"))
