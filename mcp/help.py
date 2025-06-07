HELP_DATA = {
    "botfather": {
        "send-message": {
            "description": "Send a message to BotFather",
            "args": ["--msg"]
        },
        "get-replies": {
            "description": "Get replies from BotFather",
            "args": ["--limit"]
        },
        "click-button": {
            "description": "Click a button in BotFather's message",
            "args": ["--button-text", "--msg-id"]
        }
    }
}

def get_help():
    return {"plugins": HELP_DATA} 