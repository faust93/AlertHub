#!/usr/bin/env python3
import eventlet
eventlet.monkey_patch()
from psycogreen.eventlet import patch_psycopg
patch_psycopg()
#import eventlet.wsgi
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_socketio import SocketIO, emit
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
import json, jinja2
import hashlib
import base64
import logging
import os, signal, sys, atexit
from threading import Event

import config
from utils.postgres import AlertsDatabase
from utils.pipeline import AlertPipeline
from utils.pipeline_validator import PipelineValidator

logging.basicConfig(
    #filename='alerthub.log',
    level=logging.DEBUG,
    format= '[%(asctime)s] %(levelname)s - %(message)s',
    # format= '%(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

TZ = ZoneInfo(config.TZ)

app = Flask(__name__, static_folder='dist')

socketio = SocketIO(app, cors_allowed_origins="*",async_mode="eventlet")

app.config['JWT_SECRET_KEY'] = config.SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=config.ACCESS_TOKEN_EXPIRES)

jwt = JWTManager(app)

# Handle process termination
shutdown_event = Event()
def cleanup():
    if not shutdown_event.is_set():
        shutdown_event.set()
        logging.info("Cleaning up resources before exit...")
        if 'pipeline' in globals():
            pipeline.stop()
        logging.info("Done")

def handle_signal(signum, frame):
    logging.info(f"Received signal {signum}")
    socketio.stop()
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
atexit.register(cleanup)

# return user_role in case of successfull auth or None
def UserAuth(user_name, user_password):
    user = db.getUser(user_name)
    hashed_pass = hashlib.sha256(user_password.encode('utf-8')).digest().hex()
    if user is not None:
        if user[2] == hashed_pass:
            return user[1], user[3], user[9]  # return name, role, timezone
        else:
            return None, None, None
    else:
        return None, None, None

@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


# Alertmanager Webhook endpoint
@app.route('/alertmanager', methods=['POST'])
def alertHook():
    try:
        payload = request.json
        if payload['alerts'] is not None:
            for alert in payload['alerts']:
                _alert = db.upsert(alert)
                if _alert is not None:
                    pipeline.add_task("alert", _alert)

                    _alert_temp = _alert.copy()
                    starts_at = _alert_temp.get('startsAt',None)
                    ends_at = _alert_temp.get('endsAt', None)
                    updated_at = _alert_temp.get('updatedAt',None)
                    if starts_at is not None:
                        _alert_temp['startsAt'] = datetime.fromtimestamp(starts_at, tz=TZ).isoformat()
                    if ends_at is not None:
                        _alert_temp['endsAt'] = datetime.fromtimestamp(ends_at, tz=TZ).isoformat()
                    if updated_at is not None:
                        _alert_temp['updatedAt'] = datetime.fromtimestamp(updated_at, tz=TZ).isoformat()
                    socketio.emit("alert_update", {"data": _alert_temp})

        return "", 200
    except ValueError:
        return 'Invalid JSON', 400

# REST API endpoints
@app.route('/auth/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400

    user_name, user_role, tz = UserAuth(username, password)
    if user_role is None or user_name is None:
        logging.error(f"Failed user login attempt: {username}")
        return jsonify({"msg": "Invalid credentials"}), 403

    additional_claims = {"role": user_role, "timezone": tz}
    access_token = create_access_token(identity=user_name, additional_claims=additional_claims)
    logging.info(f"Successful user login: {user_name}")
    return jsonify({ "token": access_token, "user_id": user_name, "role": user_role, "timezone": tz}), 200

@app.route('/api/v1/alertHistory', methods=['GET'])
@jwt_required()
def alertHistory():
    alert_id = request.args.get('id', 0)
    limit = request.args.get('limit', 100)
    if alert_id == 0:
        return jsonify({"error": "wrong arguments" })

    rows = db.queryAlertHistory(alert_id, limit)

    hist = []
    if rows is None:
        return jsonify({"alert_history": hist})

    for al in rows:
        timestamp = datetime.fromtimestamp(al[1], tz=TZ).isoformat()
        event_timestamp = datetime.fromtimestamp(al[2], tz=TZ).isoformat()

        hist.append({
            "_id": al[0],
            "timestamp": timestamp,
            "event_timestamp": event_timestamp,
            "alert_id": al[3],
            "status": al[4],
            "comment": al[5]
        })

    return jsonify({"alert_history": hist})

@app.route('/api/v1/setAlertStatus', methods=['POST'])
@jwt_required()
def setAlertStatus():
    data = request.get_json()
    required_fields = ['alert_id', 'status', 'comment']
    missing_fields = [field for field in required_fields if not field in data]

    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    fingerprint = data['alert_id']
    status = data['status']
    comment = data['comment']
    hist_update = data.get('update_history', True)
    hist_status = data.get('history_status', status)

    if status not in ['acked', 'muted', 'unmuted', 'resolved', 'firing']:
        return jsonify({
            "msg": "Invalid status"
        }), 400

    if db.setAlertStatus(fingerprint, status, comment, hist_update, hist_status):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/deleteAlert', methods=['GET'])
@jwt_required()
def deleteAlert():
    alert_id = request.args.get('id', None)
    if alert_id is None:
        return jsonify({"error": "wrong arguments" })
    if db.deleteAlert(alert_id):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Return an alert by Id
# Args: id=<alert_id>
@app.route('/api/v1/alert', methods=['GET'])
@jwt_required()
def alertId():
    alert_id = request.args.get('id', 0)
    if alert_id == 0:
        return jsonify({"error": "wrong arguments" })

    rows = db.queryAlertId(alert_id)

    alerts = []
    if rows is None:
        return jsonify({"alerts": alerts})

    for al in rows:
        updatedAt = datetime.fromtimestamp(al[10], tz=TZ).isoformat()
        if al[11] > 0:
            endsAt = datetime.fromtimestamp(al[11], tz=TZ).isoformat()
        else:
            endsAt = 0
        startsAt = datetime.fromtimestamp(al[12], tz=TZ).isoformat()

        alerts.append({
            "_id": al[0],
            "alert_id": al[1],
            "alertname": al[2],
            "severity": al[3],
            "instance": al[4],
            "job": al[5],
            "status": al[6],
            "annotations": al[7],
            "labels": al[8],
            "generatorURL": al[9],
            "updatedAt": updatedAt,
            "startsAt": startsAt,
            "endsAt": endsAt,
            "alert_count": al[13]
        })

    return jsonify({"alerts": alerts})

# Return alerts for specific time range
# Args: from=<ISO Timestamp> to=<ISO Timestamp>
@app.route('/api/v1/alertsRange', methods=['GET'])
@jwt_required()
def alertRange():
    tm_from = request.args.get('from', None)
    tm_to = request.args.get('to', None)
    status = request.args.get('status', None)
    search = request.args.get('fts', None)
    offset = request.args.get('offset', 0)
    limit = request.args.get('limit', 500)

    history = request.args.get('history', False)
    if 'true' in history:
        history = True
    else:
        history = False

    if len(search) < 3:
        search = None

    rows = db.queryAlertsRange(range_start=tm_from, range_end=tm_to, fts=search, status=status, offset=offset, limit=limit, history=history)

    alerts = []
    if rows is None:
        return jsonify({"alerts": alerts, "total": 0})

    for al in rows:
        updatedAt = datetime.fromtimestamp(al[10], tz=TZ).isoformat()
        if al[11] > 0:
            endsAt = datetime.fromtimestamp(al[11], tz=TZ).isoformat()
        else:
            endsAt = 0
        startsAt = datetime.fromtimestamp(al[12], tz=TZ).isoformat()

        alerts.append({
            "_id": al[0],
            "alert_id": al[1],
            "alertname": al[2],
            "severity": al[3],
            "instance": al[4],
            "job": al[5],
            "status": al[6],
            "annotations": al[7],
            "labels": al[8],
            "generatorURL": al[9],
            "updatedAt": updatedAt,
            "startsAt": startsAt,
            "endsAt": endsAt,
            "alert_count": al[13]
        })

    total = rows[0][14] if len(rows) > 0 and len(rows[0]) > 14 else 0
    return jsonify({"alerts": alerts, "total": total})

@app.route('/api/v1/searchSave', methods=['POST'])
@jwt_required()
def searchSave():
    data = request.get_json()
    required_fields = ['name', 'query', 'user_id']
    missing_fields = [field for field in required_fields if not data.get(field)]

    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    query = data['query']
    shared = data['shared']
    user_id = data['user_id']

    shared = 1 if shared else 0
    if db.saveSearch(name, query, shared, user_id):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/searchUpdate', methods=['POST'])
@jwt_required()
def searchUpdate():
    user_id = get_jwt_identity()
    role = get_jwt()['role']

    data = request.get_json()
    required_fields = ['id', 'name', 'query', 'user_id']
    missing_fields = [field for field in required_fields if not data.get(field)]

    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    sid = data['id']
    name = data['name']
    query = data['query']
    shared = data['shared']
    user_id = data['user_id']

    if user_id != name and role != 0:
        return jsonify({
            "msg": "Permission denied"
        }), 400

    shared = 1 if shared else 0
    if db.updateSearch(sid, name, query, shared, user_id):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/searchLoad', methods=['GET'])
@jwt_required()
def searchLoad():
    rows = db.loadSearch()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    if rows is None:
        return jsonify([])
    search = [
        {
            "id": s[0],
            "shared": s[1],
            "user_id": s[2],
            "name": s[3],
            "query": s[4]
        }
        for s in rows
    ]
    return jsonify(search)

@app.route('/api/v1/searchDelete', methods=['GET'])
@jwt_required()
def searchDelete():
    sid = request.args.get('id', None)

    if sid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deleteSearch(sid):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# User API endpoints
@app.route('/api/v1/getUsers', methods=['GET'])
@jwt_required()
def getUsers():
    try:
        rows = db.getUsers()
        if rows is False:
            return jsonify({ "msg": "DB Error" }), 500
        if rows is None:
            return jsonify([])
        users = [
            {
                "id": u[0],
                "name": u[1],
                "role": u[3],
                "email": u[4],
                "notifiers": u[5],
                "telegram_id": u[6],
                "ntfy": u[7],
                "apprise": u[8],
                "timezone": u[9]
            }
            for u in rows
        ]
        return jsonify(users)
    except Exception as e:
        logging.error(f"Error in getUsers: {e}")
        return jsonify({"msg": "Internal server error"}), 500

@app.route('/api/v1/addUser', methods=['POST'])
@jwt_required()
def addUser():
    try:
        role = get_jwt()['role']
        if role != 0:
            return jsonify({
                "msg": "Permission denied"
            }), 400

        data = request.get_json()

        required_fields = ['name', 'password', 'email', 'notifiers', 'telegram_id', 'ntfy', 'apprise', 'timezone', 'role']
        missing_fields = [field for field in required_fields if not field in data]

        if missing_fields:
            return jsonify({
                "msg": "Missing or empty required fields",
                "fields": missing_fields
            }), 400

        name = data['name']
        password = data['password']
        email = data['email']
        notifiers = data['notifiers']
        user_role = data['role']
        telegram_id = data['telegram_id']
        ntfy = data['ntfy']
        apprise = data['apprise']
        timezone = data['timezone']

        if db.getUser(name) is not None:
            return jsonify({
                "msg": "User already exists"
            }), 400

        hashed_pass = hashlib.sha256(password.encode('utf-8')).digest().hex()
        if  db.putUser(name, hashed_pass, user_role, email, notifiers, telegram_id, ntfy, apprise, timezone):
            return jsonify({ "msg": "ok" }), 200
        else:
            return jsonify({ "msg": "DB Error" }), 500

        return jsonify({ "msg": "ok" }), 200
    except Exception as e:
        logging.error(f"Error in addUser: {e}")
        return jsonify({"msg": "Internal server error"}), 500

@app.route('/api/v1/updateUser', methods=['POST'])
@jwt_required()
def updateUser():
    data = request.get_json()
    required_fields = ['name', 'password', 'email', 'notifiers', 'telegram_id', 'ntfy', 'apprise', 'timezone', 'role']
    missing_fields = [field for field in required_fields if not field in data]

    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    password = data['password']
    email = data['email']
    notifiers = data['notifiers']
    user_role = data['role']
    telegram_id = data['telegram_id']
    ntfy = data['ntfy']
    apprise = data['apprise']
    pass_update = data.get('password_update', int(1))
    timezone = data['timezone']

    role = get_jwt()['role']
    user_id = get_jwt_identity()

    if not (user_id == name or role == 0):
        return jsonify({
            "msg": "Permission denied"
        }), 400

    if db.getUser(name) is None:
        return jsonify({
            "msg": "No such user"
        }), 400

    hashed_pass = hashlib.sha256(password.encode('utf-8')).digest().hex()
    if db.updateUser(name, hashed_pass, user_role, email, notifiers, telegram_id, ntfy, apprise, timezone, pass_update):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

    return jsonify({ "msg": "ok" }), 200

@app.route('/api/v1/deleteUser', methods=['GET'])
@jwt_required()
def deleteUser():
    role = get_jwt()['role']
    if role != 0:
        return jsonify({
            "msg": "Permission denied"
        }), 400

    name = request.args.get('name', None)
    if name is None:
        return jsonify({ "msg": "name missing" }), 400

    uid = request.args.get('id', None)
    if uid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deleteUser(name) and db.deleteUserRefs(int(uid)):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Teams endpoint
@app.route('/api/v1/getTeams', methods=['GET'])
@jwt_required()
def getTeams():
    rows = db.getTeams()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    teams = []
    if rows is None:
        return jsonify([])
    for t in rows:
        teams.append({
            "id": t[0],
            "name": t[1],
            "members": t[2]
        })
    return jsonify(teams)

@app.route('/api/v1/addTeam', methods=['POST'])
@jwt_required()
def addTeam():
    role = get_jwt()['role']
    if role != 0:
        return jsonify({
            "msg": "Permission denied"
        }), 400

    data = request.get_json()

    required_fields = ['name', 'members']
    missing_fields = [field for field in required_fields if not field in data]

    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    members = data['members']
    if len(members) < 2:
        members = "[]"
    if  db.addTeam(name, members):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/updateTeam', methods=['POST'])
@jwt_required()
def updateTeam():
    role = get_jwt()['role']
    if role != 0:
        return jsonify({
            "msg": "Permission denied"
        }), 400
    user_id = get_jwt_identity()
    data = request.get_json()

    required_fields = ['id', 'name', 'members']
    missing_fields = [field for field in required_fields if not field in data]

    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    tid = data['id']
    name = data['name']
    members = data['members']

    if db.updateTeam(int(tid), name, members):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

    return jsonify({ "msg": "ok" }), 200

@app.route('/api/v1/deleteTeam', methods=['GET'])
@jwt_required()
def deleteTeam():
    role = get_jwt()['role']
    if role != 0:
        return jsonify({
            "msg": "Permission denied"
        }), 400

    tid = request.args.get('id', None)
    if tid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deleteTeam(int(tid)):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Schedules
@app.route('/api/v1/getSchedules', methods=['GET'])
@jwt_required()
def getSchedules():
    rows = db.getSchedules()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    scheds = []
    if rows is None:
        return jsonify([])
    for s in rows:
        scheds.append({
            "id": s[0],
            "name": s[1],
            "group_id": s[2],
            "starts_at": datetime.fromtimestamp(s[3], tz=TZ).isoformat(),
            "ends_at": datetime.fromtimestamp(s[4], tz=TZ).isoformat(),
            "mute_starts": s[5],
            "mute_ends": s[6],
            "people": s[7]
        })
    return jsonify(scheds)

@app.route('/api/v1/addSchedule', methods=['POST'])
@jwt_required()
def addSchedule():
    data = request.get_json()
    #print(data)
    required_fields = ['name', 'group_id', 'starts_at', 'ends_at', 'people', 'mute_starts', 'mute_ends']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    group_id = data['group_id']
    people = '[]' if len(data['people']) < 2 else data['people']

    starts_at = datetime.fromisoformat(data['starts_at']).timestamp()
    ends_at = datetime.fromisoformat(data['ends_at']).timestamp()

    mute_ends = data['mute_ends']
    mute_starts = data['mute_starts']

    if db.addSchedule(name, group_id, starts_at, ends_at, mute_starts, mute_ends, people):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/updateSchedule', methods=['POST'])
@jwt_required()
def updateSchedule():
    data = request.get_json()

    required_fields = ['id', 'name', 'group_id', 'starts_at', 'ends_at', 'people', 'mute_starts', 'mute_ends']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    sid = data['id']
    name = data['name']
    group_id = data['group_id']
    people = '[]' if len(data['people']) < 2 else data['people']

    starts_at = datetime.fromisoformat(data['starts_at']).timestamp()
    ends_at = datetime.fromisoformat(data['ends_at']).timestamp()

    mute_ends = data['mute_ends']
    mute_starts = data['mute_starts']

    if db.updateSchedule(sid, name, group_id, starts_at, ends_at, mute_starts, mute_ends, people):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/deleteSchedule', methods=['GET'])
@jwt_required()
def deleteSchedule():
    sid = request.args.get('id', None)
    if sid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deleteSchedule(sid):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Schedule groups
@app.route('/api/v1/getScheduleGroups', methods=['GET'])
@jwt_required()
def getScheduleGroups():
    rows = db.getScheduleGroups()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    schg = []
    if rows is None:
        return jsonify([])
    for s in rows:
        schg.append({
            "id": s[0],
            "name": s[1],
            "pipeline_id": s[2],
            "team_id": s[3]
        })
    return jsonify(schg)

@app.route('/api/v1/addScheduleGroup', methods=['POST'])
@jwt_required()
def addScheduleGroup():
    data = request.get_json()

    required_fields = ['name', 'pipeline_id', 'team_id']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    pipeline_id = data['pipeline_id']
    team_id = data['team_id']

    if db.addScheduleGroup(name, pipeline_id, team_id):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/updateScheduleGroup', methods=['POST'])
@jwt_required()
def updateScheduleGroup():
    data = request.get_json()

    required_fields = ['id', 'name', 'pipeline_id', 'team_id']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    sid = data['id']
    name = data['name']
    pipeline_id = data['pipeline_id']
    team_id = data['team_id']

    if db.updateScheduleGroup(sid, name, pipeline_id, team_id):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/deleteScheduleGroup', methods=['GET'])
@jwt_required()
def deleteScheduleGroup():
    gid = request.args.get('id', None)
    if gid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deleteScheduleGroup(gid):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Maintenance
@app.route('/api/v1/getMaintenances', methods=['GET'])
@jwt_required()
def getMaintenances():
    rows = db.getMaintenances()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500
    if rows is None:
        return jsonify([])
    mnts = [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "filter": r[3],
            "oncall_groups": r[4],
            "starts_at": datetime.fromtimestamp(r[5], tz=TZ).isoformat(),
            "ends_at": datetime.fromtimestamp(r[6], tz=TZ).isoformat()
        }
        for r in rows
    ]
    return jsonify(mnts)

@app.route('/api/v1/addMaintenance', methods=['POST'])
@jwt_required()
def addMaintenance():
    data = request.get_json()
    required_fields = ['name', 'description', 'filter', 'oncall_groups', 'starts_at', 'ends_at']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    description = data['description']
    filter = data['filter']
    ocgroups = data['oncall_groups']
    starts_at = datetime.fromisoformat(data['starts_at']).timestamp()
    ends_at = datetime.fromisoformat(data['ends_at']).timestamp()

    if db.addMaintenance(name, description, filter, ocgroups, starts_at, ends_at):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/updateMaintenance', methods=['POST'])
@jwt_required()
def updateMaintenance():
    data = request.get_json()
    required_fields = ['id', 'name', 'description', 'filter', 'oncall_groups', 'starts_at', 'ends_at']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    mid = data['id']
    name = data['name']
    description = data['description']
    filter = data['filter']
    ocgroups = data['oncall_groups']
    starts_at = datetime.fromisoformat(data['starts_at']).timestamp()
    ends_at = datetime.fromisoformat(data['ends_at']).timestamp()

    if db.updateMaintenance(mid, name, description, filter, ocgroups, starts_at, ends_at):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/deleteMaintenance', methods=['GET'])
@jwt_required()
def deleteMaintenance():
    mid = request.args.get('id', None)
    if mid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deleteMaintenance(mid):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Pipelines
@app.route('/api/v1/getPipelines', methods=['GET'])
@jwt_required()
def getPipelines():
    rows = db.getPipelines()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    pips = []
    if rows is None:
        return jsonify([])
    for p in rows:
        pips.append({
            "id": p[0],
            "name": p[1],
            "description": p[2],
            "yaml_content": p[3]
        })
    return jsonify(pips)

@app.route('/api/v1/addPipeline', methods=['POST'])
@jwt_required()
def addPipeline():
    data = request.get_json()

    required_fields = ['name','description','yaml_content']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    description = data['description']
    yaml_content = data['yaml_content']

    if db.addPipeline(name, description, yaml_content):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/updatePipeline', methods=['POST'])
@jwt_required()
def updatePipeline():
    data = request.get_json()

    required_fields = ['id', 'name', 'description', 'yaml_content']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    pid = data['id']
    name = data['name']
    description = data['description']
    yaml_content = data['yaml_content']

    if db.updatePipeline(pid, name, description, yaml_content):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/deletePipeline', methods=['GET'])
@jwt_required()
def deletePipeline():
    pid = request.args.get('id', None)
    if pid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deletePipeline(pid):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Templates
@app.route('/api/v1/getTemplates', methods=['GET'])
@jwt_required()
def getTemplates():
    rows = db.getTemplates()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500
    if not rows:
        return jsonify([])
    tpls = [
        {
            "id": t[0],
            "name": t[1],
            "description": t[2],
            "template": t[3],
        }
        for t in rows
    ]
    return jsonify(tpls)

@app.route('/api/v1/addTemplate', methods=['POST'])
@jwt_required()
def addTemplate():
    data = request.get_json()

    required_fields = ['name','description','template']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    name = data['name']
    description = data['description']
    template = data['template']

    if db.addTemplate(name, description, template):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/updateTemplate', methods=['POST'])
@jwt_required()
def updateTemplate():
    data = request.get_json()

    required_fields = ['id', 'name', 'description', 'template']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    tid = data['id']
    name = data['name']
    description = data['description']
    template = data['template']

    if db.updateTemplate(tid, name, description, template):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

@app.route('/api/v1/deleteTemplate', methods=['GET'])
@jwt_required()
def deleteTemplate():
    tid = request.args.get('id', None)
    if tid is None:
        return jsonify({ "msg": "id missing" }), 400

    if db.deleteTemplate(tid):
        return jsonify({ "msg": "ok" }), 200
    else:
        return jsonify({ "msg": "DB Error" }), 500

# Stats
@app.route('/api/v1/alertStats', methods=['GET'])
@jwt_required()
def getAlertStats():
    rows = db.getAlertStatusStats()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    status = [
        {
            "status": r[0],
            "total": r[1],
        }
        for r in rows
    ]

    rows = db.getAlertSeverityStats()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    severity = [
        {
            "severity": r[0],
            "total": r[1],
        }
        for r in rows
    ]

    rows = db.getAlertNameStats()
    if rows is False:
        return jsonify({ "msg": "DB Error" }), 500

    alert_name = [
        {
            "name": r[0],
            "severity": r[1],
            "total": r[2],
        }
        for r in rows
    ]

    return jsonify({"status": status, "severity": severity, "alert_name": alert_name})

# Utils
@app.route('/api/v1/renderTemplate', methods=['POST'])
@jwt_required()
def renderTemplate():
    data = request.get_json()

    required_fields = ['alert_json', 'template']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    alert_json = data['alert_json']
    template = data['template']

    try:
        alert = json.loads(alert_json)
        env = jinja2.Environment(
            autoescape=False,
            trim_blocks=False,
            lstrip_blocks=False
            )
        tpl = env.from_string(template)
        result = tpl.render(alert)
    except (json.JSONDecodeError, jinja2.TemplateError) as e:
        logging.error("Error processing alert: %s", e, exc_info=True)
        result = str(e)

    return jsonify({ "msg": "ok", "result": result }), 200

# pipeline validator
@app.route('/api/v1/validatePipeline', methods=['POST'])
@jwt_required()
def validatePipeline():
    data = request.get_json()

    required_fields = ['pipeline']
    missing_fields = [field for field in required_fields if not field in data]
    if missing_fields:
        return jsonify({
            "msg": "Missing or empty required fields",
            "fields": missing_fields
        }), 400

    pipeline_dsl = data['pipeline']
    validator = PipelineValidator()
    err, result = validator.validate_pipeline(pipeline_dsl)
    if err:
        logging.error("Error validating pipeline dsl: %s", result)
    else:
        logging.info("Pipeline dsl validation successful: %s", result)
        result = "OK"
    return jsonify({ "msg": "ok", "result": result }), 200

@socketio.on('connect')
def handle_connect():
    logging.info("Incoming WebSocket frontend connection..")

@socketio.on('disconnect')
def handle_connect():
    logging.info("WS disconnected..")

if __name__ == '__main__':
    try:
        db = AlertsDatabase(config.DATABASE_URL)
        db.init_db()
    except:
        raise Exception("Failed to initialize database")

    pipeline = AlertPipeline(db)
    pipeline.start()

    try:
        socketio.run(app, host=config.LISTEN_ADDRESS, port=config.LISTEN_PORT)
    finally:
        cleanup()
