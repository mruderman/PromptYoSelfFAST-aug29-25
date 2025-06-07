#!/usr/bin/env python3
import argparse
import json
import sys

def click_button(button_text: str, msg_id: int) -> dict:
    """Mock function to click a button in BotFather."""
    return {
        "result": f"Clicked button {button_text} on message {msg_id}"
    }

def main():
    parser = argparse.ArgumentParser(description="Mock BotFather CLI")
    parser.add_argument("command", nargs="?")
    parser.add_argument("--button-text")
    parser.add_argument("--msg-id", type=int)
    args, unknown = parser.parse_known_args()

    def out(obj, is_error=False):
        print(json.dumps(obj))

    if args.command == "click-button":
        if not args.button_text or args.msg_id is None:
            out({"error": "Missing required arguments"}, is_error=True)
            sys.exit(1)
        result = click_button(args.button_text, args.msg_id)
        out(result)
        sys.exit(0)
    else:
        out({"error": f"Unknown command: {args.command}"}, is_error=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 