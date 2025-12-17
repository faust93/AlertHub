def up(cursor):
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Alerts (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                alert_id TEXT NOT NULL,
                alertname TEXT NOT NULL,
                severity TEXT NOT NULL,
                instance TEXT,
                job TEXT NOT NULL,
                status TEXT NOT NULL,
                annotations JSONB,
                labels JSONB,
                generatorURL TEXT,
                updatedAt BIGINT,
                endsAt BIGINT,
                startsAt BIGINT,
                alert_count SMALLINT,
                search_fts TSVECTOR
                    GENERATED ALWAYS AS (to_tsvector('simple', status) || ' ' ||
                                         to_tsvector('simple', alert_id) || ' ' ||
                                         jsonb_to_tsvector('simple', labels, '"all"') || ' ' ||
                                         jsonb_to_tsvector('simple', annotations, '["string", "numeric"]')) STORED
            )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_fts ON Alerts USING GIN(search_fts)')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS AlertsHistory (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                timestamp BIGINT NOT NULL,
                event_timestamp BIGINT NOT NULL,
                alert_id TEXT NOT NULL,
                status TEXT NOT NULL,
                comment TEXT
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS SearchFilters (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                shared INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                query TEXT NOT NULL
            )
    ''')
# notifier values:
# 0 = None
# 1 = Email
# 2 = Telegram
# 3 = Ntfy
# 4 = Apprise
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role INTEGER NOT NULL,
                email TEXT NOT NULL,
                notifiers JSONB,
                telegram_id TEXT NOT NULL,
                ntfy TEXT NOT NULL,
                apprise TEXT NOT NULL,
                timezone TEXT NOT NULL DEFAULT 'Local'
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Teams (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                members JSONB
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Schedules (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                group_id BIGINT,
                starts_at BIGINT NOT NULL,
                ends_at BIGINT NOT NULL,
                mute_starts TEXT,
                mute_ends TEXT,
                people JSONB
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS ScheduleGroups (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                pipeline_id BIGINT,
                team_id BIGINT
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Maintenance (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                filter TEXT,
                oncall_groups JSONB,
                starts_at BIGINT NOT NULL,
                ends_at BIGINT NOT NULL
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Pipelines(
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                yaml_content TEXT NOT NULL
            )
    ''')
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS Templates(
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                template TEXT NOT NULL
            )
    ''')

# default admin
    cursor.execute('''
            INSERT INTO Users (name, password, role, email, notifiers, telegram_id, ntfy, apprise)
                VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 0, 'admin@company.com', '[]', '', '', '')
    ''')
