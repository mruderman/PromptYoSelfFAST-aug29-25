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
    parser.add_argument("command", choices=["click-button"])
    parser.add_argument("--button-text", required=True)
    parser.add_argument("--msg-id", type=int, required=True)
    
    args = parser.parse_args()
    
    if args.command == "click-button":
        result = click_button(args.button_text, args.msg_id)
        print(json.dumps(result))
        sys.exit(0)
    else:
        print(json.dumps({"error": f"Unknown command: {args.command}"}))
        sys.exit(1)

if __name__ == "__main__":
    main() 