from flask import Flask, request, jsonify, send_from_directory
import dialogflow_v2beta1 as dialogflow
import json
import uuid
import os

from coco import ConversationalComponent

# Consts.
CURRENT_SESSION_ID = str(uuid.uuid4())
MAIN_COMP = "default"

# Current component on which the session is running.
current_comp = MAIN_COMP

# Init app.
app = Flask(__name__)


# Set DialogFlow Auth.
session_client = dialogflow.SessionsClient.from_service_account_json("banking.json")

with open("banking.json", "r") as f:
    sacc = json.load(f)

project_id = sacc["project_id"]


# Processors.
def process_dialogflow(session_id, text, language_code="en"):
    """
    Returns bot output for user input.

    Using the same `session_id` between requests allows continuation
    of the conversation.

    Arguments:
        session_id (string): Current session ID.
        text (string): User input.
        language_code (string): Context language.
    Returns:
        Return tuple intent_name, bot_output (tuple).
    """

    session = session_client.session_path(project_id, session_id)

    text_input = dialogflow.types.TextInput(text=text,
                                            language_code=language_code)

    query_input = dialogflow.types.QueryInput(text=text_input)

    response = session_client.detect_intent(session=session,
                                            query_input=query_input)

    return response.query_result.intent.display_name, response.query_result.fulfillment_text


def process_coco(component_id, session_id, input_text):
    """
    Process user input at a coco component.

    Arguments:
        component_id (string): Target component ID.
        session_id (string): Target session ID.
        input_text (string): User input text.

    Returns:
        CoCo component output. (string)
    """
    component = ConversationalComponent(component_id)

    return component(session_id=session_id, user_input=input_text)


@app.route("/input", methods=["POST"])
def get_input():
    global current_comp
    request_data = request.get_json() or {}
    user_input = request_data.get("user_input")

    # Get response from DialogFlow for user input.
    intent_name, bot_output = process_dialogflow(session_id=CURRENT_SESSION_ID,
                                                 text=user_input)

    # If catch intent, give control to CoCo component.
    if intent_name == "account.open":
        current_comp = "register_vp3"

    if current_comp == "register_vp3":
        # Fetch response from CoCo if intent catch.
        coco_response = process_coco(component_id="register_vp3",
                                     session_id=CURRENT_SESSION_ID,
                                     input_text=user_input)

        # If component done, return the control to the main flow.
        if coco_response.component_done:
            current_comp = MAIN_COMP

        bot_output = coco_response.response

    return jsonify({"response": bot_output}), 200, {}


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


if __name__ == "__main__":
    app.run(port=8080, host='0.0.0.0')
