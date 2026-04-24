"""
get_token.py
Ejecutá este script UNA VEZ en tu máquina local para obtener el refresh_token
que vas a guardar como variable de entorno en Heroku.

Uso:
    pip install google-auth-oauthlib
    python get_token.py
"""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Pegá aquí tus credenciales de Google Cloud Console
CLIENT_CONFIG = {
    "installed": {
        "client_id": "TU_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "TU_CLIENT_SECRET",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}

def main():
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n✅ Autenticación exitosa. Guardá estos valores en Heroku:\n")
    print(f"GOOGLE_CLIENT_ID={CLIENT_CONFIG['installed']['client_id']}")
    print(f"GOOGLE_CLIENT_SECRET={CLIENT_CONFIG['installed']['client_secret']}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("\nComando para Heroku:")
    print(f"heroku config:set \\")
    print(f"  GOOGLE_CLIENT_ID=\"{CLIENT_CONFIG['installed']['client_id']}\" \\")
    print(f"  GOOGLE_CLIENT_SECRET=\"{CLIENT_CONFIG['installed']['client_secret']}\" \\")
    print(f"  GOOGLE_REFRESH_TOKEN=\"{creds.refresh_token}\"")

if __name__ == "__main__":
    main()
