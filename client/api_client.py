import requests

BASE_URL = "http://127.0.0.1:8000"


def get_greeting_from_api(name: str) -> tuple[dict | None, str | None]:
    try:
        api_url = f"{BASE_URL}/api/greet"
        params = {"name": name}

        response = requests.get(api_url, params=params, timeout=5)

        response.raise_for_status()

        data = response.json()
        return data, None

    except requests.exceptions.Timeout:
        return None, "Request timed out. Please check your network or if the backend is running."
    except requests.exceptions.ConnectionError:
        return None, "Connection error. Could not connect to the backend service."
    except requests.exceptions.RequestException as e:
        return None, f"A network error occurred: {e}"
    except Exception as e:
        return None, f"An unknown error occurred: {e}"