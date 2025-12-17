# AlertHub Configuration
LISTEN_ADDRESS = "0.0.0.0"
LISTEN_PORT = 5000
BASE_URL = "https://alerthub.domain.net"

# Alertmanager's alert timestamps are in UTC
# Specify local timezone here for correct date formatting during API calls
# Leave default to provide timestamps as is (UTC)
# Alerthub UI uses browser local timezone by default. Could be overridden in user's preferences
TZ = "UTC"
# TZ = "Europe/Tallinn"

# PostgreSQL
DATABASE_URL = "dbname=alerthub user=alerthub password=alerthub123 host=alerthub-postgres"

# JWT
SECRET_KEY = "JWT_SECRET_KEY"
ACCESS_TOKEN_EXPIRES = 24

# Notifications
TELEGRAM_BOT_TOKEN = "TG_BOT_TOKEN"

NTFY_SERVER = "https://ntfy.domain.net"
NTFY_ACCESS_TOKEN = "NTFY_TOKEN"
