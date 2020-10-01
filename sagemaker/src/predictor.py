import json
import logging

import flask
from flask import jsonify, request

from werkzeug.exceptions import HTTPException


# logging
logger = logging.getLogger(__name__)

# flask app
app = flask.Flask(__name__)


@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


@app.route('/ping', methods=['GET'])
def ping():
    status = 200
    return jsonify(status=status), status


@app.route('/invocations', methods=['POST'])
def predict():
    content = request.get_json(silent=True)
    return jsonify(predictions=content), 200
