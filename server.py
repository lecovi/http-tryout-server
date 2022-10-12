import hashlib
import json
from datetime import datetime
from os import getenv

from flask import Flask, Request, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from werkzeug.datastructures import EnvironHeaders, ImmutableMultiDict

DB_PASSWORD = getenv("DB_PASSWORD")
DB_URI = f"postgresql://postgres:{DB_PASSWORD}@db:5432/postgres"


def parse_request_var_to_value_for_dict(value):
    if isinstance(value, EnvironHeaders):
        return value.to_wsgi_list()
    if isinstance(value, ImmutableMultiDict):
        return value.to_dict()
    if isinstance(value, bytes):
        return value.decode()
    if isinstance(value, (str, tuple, list, bool)):
        return value
    else:
        return str(value)


class CustomRequest(Request):
    def to_dict(self):
        "Returns a dict from a Flask Request Object"
        request_as_dict = vars(self).copy()

        for k, v in request_as_dict.items():
            request_as_dict[k] = parse_request_var_to_value_for_dict(v)
        return request_as_dict


class CustomFlask(Flask):
    request_class = CustomRequest


app = CustomFlask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
db = SQLAlchemy(app)


class UserRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), index=True)
    raw_data = db.Column(JSON)
    created_on = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_on = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    extra = db.Column(JSON)

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "raw_data": self.raw_data,
            "created_on": self.created_on.isoformat(),
            "updated_on": self.updated_on.isoformat()
            if self.updated_on
            else self.updated_on,
            "extra": self.extra,
        }


def get_hash_from_dict(data):
    "Returns hexdigest from a given dictionary"
    hexdigest = hashlib.sha256(json.dumps(data).encode()).hexdigest()
    return hexdigest


@app.cli.command("create-db")
def create_user():
    "Creates DB"
    db.create_all()
    app.logger.info("Database tables created!")


@app.cli.command("drop-db")
def create_user():
    "Creates DB"
    db.drop_all()
    app.logger.info("Database tables removed!")


@app.route("/")
@app.route("/json")
def home():
    user_request = {
        "start_line": {
            "http_method": request.method,
            "request_target": request.path,
            "http_version": request.environ.get("SERVER_PROTOCOL"),
        },
        "headers": {name: value for name, value in request.headers.items()},
        "body": request.data.decode(),  # FIXME: are we 100% sure that we can decode here?
    }
    timestamped_request = {"req": user_request, "timestamp": datetime.now().isoformat()}
    hashed_request = get_hash_from_dict(timestamped_request)
    extra = request.to_dict()

    record = UserRequest(key=hashed_request, raw_data=user_request, extra=extra)
    db.session.add(record)
    db.session.commit()

    url = f"{request.host_url}{hashed_request}"
    if request.path == "/json":
        response = {
            "hash": hashed_request,
            "url": url,
            "request": user_request,
        }
        return jsonify(response)
    else:
        return render_template("home.html", url=url)


@app.route("/<key>")
@app.route("/<key>/json")
def view_request(key):
    record = UserRequest.query.filter_by(key=key).first()

    if record is None:
        return "User Request Not Found", 404

    if request.path.endswith("/json"):
        return jsonify(record.to_dict())

    return render_template("requests.html", record=record)
