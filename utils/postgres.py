import importlib
import psycopg2.pool
from datetime import datetime, timedelta
import os
import json
import logging

class AlertsDatabase:
    def __init__(self, path):
        try:
            self.cpool = psycopg2.pool.SimpleConnectionPool(1, 50, path)
        except:
            raise Exception("Unable to create Postgres connection pool")

    def get_applied_versions(self, cursor):
        cursor.execute("SELECT version FROM migrations")
        return {row[0] for row in cursor.fetchall()}

    def apply_migration(self, cursor, version, name):
        logging.info(f"Apply DB migration: {version}_{name}")
        try:
            module = importlib.import_module(f"migrations.{version}_{name}")
            if hasattr(module, 'up'):
                module.up(cursor)
            cursor.execute("INSERT INTO migrations (version) VALUES (%s)", (version,))
        except Exception as e:
            logging.error(f"Failed to run migration for {version}: {e}")

    def init_db(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            db.commit()

            applied = self.get_applied_versions(cursor)
            migration_files = sorted([f for f in os.listdir("migrations") if f.endswith(".py")])
            for mf in migration_files:
                if '__init__.py' in mf:
                    continue
                _vn = mf.split("_")
                version = _vn[0]
                name = _vn[1]
                if version not in applied:
                    name = name.replace("/", ".").replace(".py", "")
                    self.apply_migration(cursor, version, name)
            db.commit()
            cursor.close()
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database migration error: {e}")
        finally:
            if db:
                self.cpool.putconn(db)

    # Alerts
    def getAlertState(self, alert_id):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT alert_id, status, alert_count FROM Alerts WHERE alert_id=%s", (alert_id,))
            row = cursor.fetchone()
            cursor.close()
            if row is not None:
                return row[0], row[1], row[2]
            else:
                return None, None, None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return None, None
        finally:
            if db:
                self.cpool.putconn(db)

    def setAlertStatus(self, alert_fingerprint, status, comment, update_history = True, history_status = None):
        db = None
        timestamp = int(datetime.now().timestamp())
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE Alerts SET status=%s WHERE alert_id=%s", (status, alert_fingerprint))
            if update_history:
                if history_status != status and history_status is not None:
                    status = history_status
                cursor.execute("INSERT INTO AlertsHistory (timestamp, event_timestamp, alert_id, status, comment) VALUES (%s, %s, %s, %s, %s)", (timestamp, 0, alert_fingerprint, status, comment))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteAlert(self, alert_fingerprint):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM Alerts WHERE alert_id=%s", (alert_fingerprint,))
            cursor.execute("DELETE FROM AlertsHistory WHERE alert_id=%s", (alert_fingerprint,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def upsert(self, alert):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()

            fingerprint = alert['fingerprint']
            alertid, status, alert_count = self.getAlertState(fingerprint)

            logging.debug(f"Alert {fingerprint} {alertid} {alert_count} {status} to {alert['status']}")

            job = alert['labels'].get('job', "-")
            instance  = alert['labels'].get('instance', "-")
            severity =  alert['labels'].get('severity', "-")
            alertname = alert['labels'].get('alertname', "-")
            generatorURL = alert.get('generatorURL', "-")

            startsAt = datetime.fromisoformat(alert['startsAt']).timestamp()
            endsAt = datetime.fromisoformat(alert['endsAt']).timestamp()
            updatedAt = int(datetime.now().timestamp())

            if endsAt < 0:
                endsAt = 0

            if alertid == fingerprint:
                history_inserts = {
                    ('acked', 'resolved'): (endsAt, 'resolved'),
                    ('resolved', 'firing'): (startsAt, 'firing'),
                    ('firing', 'resolved'): (endsAt, 'resolved'),
                }
                if alert['status'] != status:
                    if status in ('muted', 'acked') and alert['status'] == 'firing':
                        alert_count += 1
                    elif status in ('muted', 'acked') and alert['status'] == 'resolved':
                        alert_count = 1
                    elif status in ('resolved', 'firing') and alert['status'] in ('firing', 'resolved'):
                        alert_count = 1

                    if (status, alert['status']) in history_inserts:
                        ts, new_status = history_inserts[(status, alert['status'])]
                        status = new_status
                        cursor.execute(
                            "INSERT INTO AlertsHistory (timestamp, event_timestamp, alert_id, status, comment) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (updatedAt, ts, fingerprint, status, '')
                        )
                    cursor.execute(
                        "UPDATE Alerts SET status=%s, updatedAt=%s, endsAt=%s, startsAt=%s, alert_count=%s "
                        "WHERE alert_id=%s",
                        (status, updatedAt, endsAt, startsAt, alert_count, fingerprint)
                    )
                else:
                    if status == 'firing':
                        alert_count += 1
                        cursor.execute(
                            "UPDATE Alerts SET status=%s, updatedAt=%s, endsAt=%s, startsAt=%s, alert_count=%s "
                            "WHERE alert_id=%s",
                            (status, updatedAt, endsAt, startsAt, alert_count, fingerprint)
                        )
                db.commit()
                cursor.close()
            else:
                alert_count = 1
                status = alert['status']
                cursor.execute("""
                    INSERT INTO Alerts (alert_id, alertname, severity, instance, job, status, annotations, labels, generatorURL, updatedAt, endsAt, startsAt, alert_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (fingerprint, alertname, severity, instance, job, status, json.dumps(alert['annotations']), json.dumps(alert['labels']), generatorURL, updatedAt, endsAt, startsAt, alert_count))
                if status == 'resolved':
                    startsAt = endsAt
                cursor.execute("INSERT INTO AlertsHistory (timestamp, event_timestamp, alert_id, status, comment) VALUES (%s, %s, %s, %s, %s)", (updatedAt, startsAt, fingerprint, status, ''))
                db.commit()
                cursor.close()
            return {"alert_id": fingerprint,
                    "alertname": alertname,
                    "severity": severity,
                    "instance": instance,
                    "job": job,
                    "status": status,
                    "annotations": alert['annotations'],
                    "labels": alert['labels'],
                    "generatorURL": generatorURL,
                    "updatedAt": updatedAt,
                    "endsAt": endsAt,
                    "startsAt": startsAt,
                    "alert_count": alert_count}
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return None
        finally:
            if db:
                self.cpool.putconn(db)

    def queryAlertsRange(self, range_start=None, range_end=None, fts=None, status=None, offset=0, limit=10000, history=False):
        if range_start is None or range_end is None:
            now = datetime.now()
            rangeStart = now.timestamp()
            rangeEnd = (now - timedelta(days=30)).timestamp()
        else:
            rangeStart = datetime.fromisoformat(range_start).timestamp()
            rangeEnd = datetime.fromisoformat(range_end).timestamp()

        sql = list()
        sql_query = ""
        if history:
            # Consider to use "EXPLAIN (FORMAT JSON) SELECT 1 FROM /* your query */" rather than "SELECT count(*) FROM /* your query */" here?
            sql_query = """
                SELECT
                   ah.id,
                   a.alert_id,
                   a.alertname,
                   a.severity,
                   a.instance,
                   a.job,
                   ah.status AS status,
                   a.annotations,
                   a.labels,
                   a.generatorURL,
                   a.updatedAt,
                   a.endsAt,
                   ah.event_timestamp AS startsAt,
                   a.alert_count,
                   COUNT(*) OVER() AS total_count
                FROM Alertshistory ah
                JOIN Alerts a
                    ON a.alert_id = ah.alert_id
                WHERE ah.event_timestamp >= %s AND ah.event_timestamp <= %s
            """ % (rangeEnd, rangeStart)
        else:
            sql_query = """
                SELECT id,
                    alert_id,
                    alertname,
                    severity,
                    instance,
                    job,
                    status,
                    annotations,
                    labels,
                    generatorURL,
                    updatedAt,
                    endsAt,
                    startsAt,
                    alert_count,
                    COUNT(*) OVER() AS total_count FROM Alerts
                WHERE startsAt >= %s AND startsAt <= %s
                """ % (rangeEnd, rangeStart)

        sql.append(sql_query)
        if fts is not None:
            sql.append("AND search_fts @@ to_tsquery('simple', '%s')" % fts)
        if status is not None:
            sql.append("AND status = %s" % status)

        if history:
            sql.append("ORDER BY ah.event_timestamp DESC LIMIT %s OFFSET %s" % (limit, offset))
        else:
            sql.append("ORDER BY startsAt DESC LIMIT %s OFFSET %s" % (limit, offset))
        sql.append(";")
        query = " ".join(sql)

        #logging.debug(query)
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return None
        finally:
            if db:
                self.cpool.putconn(db)

    def queryAlertId(self, alert_id):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Alerts WHERE alert_id=%s", (alert_id,))
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return None
        finally:
            if db:
                self.cpool.putconn(db)

    def queryAlertHistory(self, alert_id, limit=100):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM AlertsHistory WHERE alert_id=%s ORDER BY timestamp DESC LIMIT %s", (alert_id, limit))
            rows = cursor.fetchall()
            cursor.close()

            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return None
        finally:
            if db:
                self.cpool.putconn(db)

    # Users
    def getUser(self, user_name):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Users WHERE name=%s OR email=%s", (user_name, user_name))
            row = cursor.fetchone()
            cursor.close()
            if row is not None:
                return row
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def getUsers(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Users ORDER BY id ASC LIMIT 500")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def putUser(self, user_name, user_password, user_role, user_email, notifiers="[]", telegram_id="", ntfy="", apprise="", timezone="Local"):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO Users (name, password, role, email, notifiers, telegram_id, ntfy, apprise, timezone) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (user_name, user_password, user_role, user_email, notifiers, telegram_id, ntfy, apprise, timezone))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)


    def updateUser(self, name, password, role, email, notifiers, telegram_id="", ntfy="", apprise="", timezone="Local", pass_update=1):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            if pass_update == 1:
                cursor.execute("UPDATE Users SET password=%s, role=%s, email=%s, notifiers=%s, telegram_id=%s, ntfy=%s, apprise=%s, timezone=%s WHERE name=%s", (password, role, email, notifiers, telegram_id, ntfy, apprise, timezone, name))
            else:
                cursor.execute("UPDATE Users SET role=%s, email=%s, notifiers=%s, telegram_id=%s, ntfy=%s, apprise=%s, timezone=%s WHERE name=%s", (role, email, notifiers, telegram_id, ntfy, apprise, timezone, name))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteUser(self, uid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM Users WHERE name=%s", (uid,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    # Saved queries
    def saveSearch(self, query_name, query, shared, user_id):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO SearchFilters (shared, user_id, name, query) VALUES (%s, %s, %s, %s)", (shared, user_id, query_name, query))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def updateSearch(self, sid, query_name, query, shared, user_id):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE SearchFilters SET shared=%s, user_id=%s, name=%s, query=%s WHERE id=%s", (shared, user_id, query_name, query, sid))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def loadSearch(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM SearchFilters ORDER BY id ASC LIMIT 200")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteSearch(self, sid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM SearchFilters WHERE id=%s", (sid))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    # Teams
    def getTeams(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Teams ORDER BY id ASC LIMIT 500")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)


    def addTeam(self, team_name, team_members="[]"):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO Teams (name, members) VALUES (%s,%s)", (team_name, team_members))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteTeam(self, tId):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM Teams WHERE id=%s", (tId,))
            cursor.execute("UPDATE ScheduleGroups SET team_id=0 WHERE team_id=%s", (tId,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def updateTeam(self, team_id, team_name, team_members):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE Teams SET name=%s, members=%s WHERE id=%s", (team_name, team_members, team_id))
            # remove user from schedules if it's not in the team anymory
            cursor.execute('''
            UPDATE Schedules
            SET people = (
                SELECT COALESCE(jsonb_agg(person_id::integer), '[]'::jsonb)
                FROM jsonb_array_elements_text(Schedules.people) AS person_id
                WHERE person_id::integer = ANY(
                    SELECT jsonb_array_elements(Teams.members)::integer
                    FROM Teams
                    JOIN ScheduleGroups ON Teams.id = ScheduleGroups.team_id
                    WHERE ScheduleGroups.id = Schedules.group_id
                    AND Teams.id = %s
                )
            )
            WHERE EXISTS (
                SELECT 1
                FROM ScheduleGroups
                JOIN Teams ON Teams.id = ScheduleGroups.team_id
                WHERE ScheduleGroups.id = Schedules.group_id
                AND Teams.id = %s
            )
            ''', (team_id,team_id))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteUserRefs(self, mId):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute('''
                UPDATE Teams
                SET members = sub.new_members::jsonb
                FROM (
                        SELECT id, jsonb_agg(value) AS new_members
                        FROM Teams,
                             jsonb_array_elements(members::jsonb) AS value
                        WHERE value != to_jsonb(%s)
                        GROUP BY id
                    ) AS sub WHERE Teams.id = sub.id
                ''', (mId,))
            cursor.execute('''
                UPDATE Schedules s
                SET people = COALESCE(
                    (
                        SELECT jsonb_agg(value)
                        FROM jsonb_array_elements(COALESCE(s.people::jsonb, '[]'::jsonb)) AS value
                        WHERE value != to_jsonb(%s)
                    ),'[]'::jsonb
                )
                ''', (mId,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

# Schedules
    def getSchedules(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Schedules ORDER BY id ASC")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def addSchedule(self, name, group_id, starts_at, ends_at, mute_start, mute_end, people="[]"):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO Schedules (name, group_id, starts_at, ends_at, mute_starts, mute_ends, people) VALUES (%s,%s,%s,%s,%s,%s,%s)", (name, group_id, starts_at, ends_at, mute_start, mute_end, people))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteSchedule(self, sid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM Schedules WHERE id=%s", (sid,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def updateSchedule(self, sid, name, group_id, starts_at, ends_at, mute_start, mute_end, people="[]"):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE Schedules SET name=%s, group_id=%s, starts_at=%s, ends_at=%s, mute_starts=%s, mute_ends=%s, people=%s WHERE id=%s", (name, group_id, starts_at, ends_at, mute_start, mute_end, people, sid))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

# Schedule groups
    def getScheduleGroups(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM ScheduleGroups ORDER BY id ASC")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def addScheduleGroup(self, name, pipeline_id, team_id):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO ScheduleGroups (name, pipeline_id, team_id) VALUES (%s, %s, %s)", (name, pipeline_id, team_id))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteScheduleGroup(self, gid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute('''
                UPDATE Maintenance s
                SET oncall_groups = COALESCE(
                    (
                        SELECT jsonb_agg(value)
                        FROM jsonb_array_elements(COALESCE(s.oncall_groups::jsonb, '[]'::jsonb)) AS value
                        WHERE value != to_jsonb(%s)
                    ),'[]'::jsonb
                )
                ''', (int(gid),))
            cursor.execute("DELETE FROM ScheduleGroups WHERE id=%s", (gid,))
            cursor.execute("UPDATE Schedules SET group_id=0 WHERE group_id=%s", (gid,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def updateScheduleGroup(self, sid, name, pipeline_id, team_id):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE ScheduleGroups SET name=%s, pipeline_id=%s, team_id=%s WHERE id=%s", (name, pipeline_id, team_id, sid))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

# Pipelines
    def getPipelines(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Pipelines ORDER BY id ASC")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def getPipeline(self, pid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Pipelines WHERE id=%s", (pid,))
            row = cursor.fetchone()
            cursor.close()
            if row is not None:
                return row
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def addPipeline(self, name, description, yaml_content):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO Pipelines (name, description, yaml_content) VALUES (%s, %s, %s)", (name, description, yaml_content))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deletePipeline(self, pid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM Pipelines WHERE id=%s", (pid,))
            cursor.execute("UPDATE ScheduleGroups SET pipeline_id=0 WHERE pipeline_id=%s", (pid,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def updatePipeline(self, pid, name, description, yaml_content):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE Pipelines SET name=%s, description=%s, yaml_content=%s WHERE id=%s", (name, description, yaml_content, pid))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

# Templates
    def getTemplates(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Templates ORDER BY id ASC")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def getTemplate(self, tid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Templates WHERE id=%s", (tid,))
            row = cursor.fetchone()
            cursor.close()
            if row is not None:
                return row
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return None
        finally:
            if db:
                self.cpool.putconn(db)

    def addTemplate(self, name, description, template):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO Templates (name, description, template) VALUES (%s, %s, %s)", (name, description, template))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteTemplate(self, tid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM Templates WHERE id=%s", (tid,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def updateTemplate(self, tid, name, description, template):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE Templates SET name=%s, description=%s, template=%s WHERE id=%s", (name, description, template, tid))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

# Maintenance
    def getMaintenances(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Maintenance ORDER BY id ASC")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def getMaintenance(self, pid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT * FROM Maintenance WHERE id=%s", (pid,))
            row = cursor.fetchone()
            cursor.close()
            if row is not None:
                return row
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def addMaintenance(self, name, description, filter, oncall_groups, starts_at, ends_at):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("INSERT INTO Maintenance (name, description, filter, oncall_groups, starts_at, ends_at) VALUES (%s,%s,%s,%s,%s,%s)", (name, description, filter, oncall_groups, starts_at, ends_at))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def deleteMaintenance(self, mid):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("DELETE FROM Maintenance WHERE id=%s", (mid,))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

    def updateMaintenance(self, mid, name, description, filter, oncall_groups, starts_at, ends_at):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("UPDATE Maintenance SET name=%s, description=%s, filter=%s, oncall_groups=%s, starts_at=%s, ends_at=%s WHERE id=%s", (name, description, filter, oncall_groups, starts_at, ends_at, mid))
            db.commit()
            cursor.close()
            return True
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

# Utils
    def getMatchingSchedules(self, range_start=None, range_end=None, limit=1000):
        if range_start is None or range_end is None:
            now = datetime.now()
            rangeStart = now.timestamp()
            rangeEnd = now.timestamp()
        else:
            rangeStart = datetime.fromisoformat(range_start).timestamp()
            rangeEnd = datetime.fromisoformat(range_end).timestamp()

        query = '''
            SELECT
                s.id,
                s.name,
                sg.name AS group,
                sg.id AS group_id,
                s.starts_at,
                s.ends_at,
                s.mute_starts,
                s.mute_ends,
                jsonb_agg(
                    DISTINCT jsonb_build_object(
                        'name', u.name,
                        'email', u.email,
                        'telegram_id', u.telegram_id,
                        'ntfy', u.ntfy,
                        'apprise', u.apprise,
                        'notifiers', u.notifiers
                    )
                ) FILTER (WHERE u.id IS NOT NULL) AS people,
                sg.pipeline_id
            FROM Schedules s
            LEFT JOIN ScheduleGroups sg ON s.group_id = sg.id
            LEFT JOIN LATERAL jsonb_array_elements_text(s.people) AS p(uid) ON TRUE
            LEFT JOIN Users u ON u.id = p.uid::bigint
            WHERE s.starts_at <= %s AND s.ends_at >= %s
            GROUP BY s.id, s.name, sg.name, sg.id, sg.pipeline_id, s.starts_at, s.ends_at, s.mute_starts, s.mute_ends
        ''' % (rangeStart, rangeEnd)

        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None

        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False

        finally:
            if db:
                self.cpool.putconn(db)

    def getMatchingMaintenance(self, range_start=None, range_end=None, limit=25):
        if range_start is None or range_end is None:
            now = datetime.now()
            rangeStart = now.timestamp()
            rangeEnd = now.timestamp()
        else:
            rangeStart = datetime.fromisoformat(range_start).timestamp()
            rangeEnd = datetime.fromisoformat(range_end).timestamp()

        query = '''
            SELECT * FROM Maintenance WHERE starts_at <= %s AND ends_at >= %s
        ''' % (rangeStart, rangeEnd)

        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None
        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False
        finally:
            if db:
                self.cpool.putconn(db)

# stats
    def getAlertStatusStats(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT status, COUNT(*) AS total FROM Alerts GROUP BY status")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None

        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False

        finally:
            if db:
                self.cpool.putconn(db)

    def getAlertSeverityStats(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT severity, COUNT(*) AS total FROM Alerts GROUP BY severity")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None

        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False

        finally:
            if db:
                self.cpool.putconn(db)

    def getAlertNameStats(self):
        db = None
        try:
            db = self.cpool.getconn()
            cursor = db.cursor()
            cursor.execute("SELECT alertname, severity, COUNT(*) AS total FROM Alerts GROUP BY alertname, severity ORDER BY total DESC")
            rows = cursor.fetchall()
            cursor.close()
            if rows is not None:
                return rows
            else:
                return None

        except (Exception, psycopg2.DatabaseError) as e:
            logging.error(f"Database error: {e}")
            return False

        finally:
            if db:
                self.cpool.putconn(db)
