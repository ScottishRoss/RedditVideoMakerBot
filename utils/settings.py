import re
from pathlib import Path
from typing import Dict, Tuple

import toml
from rich.console import Console

from utils.console import handle_input

console = Console()
config = {
    "reddit": {
        "creds": {
            "client_id": "",
            "client_secret": "",
            "username": "",
            "password": "",
            "2fa": False
        },
        "thread": {
            "random": False,
            "subreddit": "",
            "post_id": "",
            "max_comment_length": 500,
            "min_comment_length": 1,
            "post_lang": "",
            "min_comments": 20
        }
    },
    "settings": {
        "allow_nsfw": False,
        "theme": "dark",
        "times_to_run": 1,
        "opacity": 0.9,
        "storymode": False,
        "storymodemethod": 1,
        "storymode_max_length": 1000,
        "resolution_w": 1080,
        "resolution_h": 1920,
        "zoom": 1,
        "channel_name": "Reddit Tales",
        "tts": {
            "voice_choice": "tiktok",
            "random_voice": True,
            "elevenlabs_voice_name": "Bella",
            "elevenlabs_api_key": "",
            "aws_polly_voice": "Matthew",
            "streamlabs_polly_voice": "Matthew",
            "tiktok_voice": "en_us_001",
            "tiktok_sessionid": "",
            "python_voice": "1",
            "py_voice_num": "2",
            "silence_duration": 0.3,
            "no_emojis": False
        }
    },
    "ai": {
        "ai_similarity_enabled": False,
        "ai_similarity_keywords": ""
    }
}


def crawl(obj: dict, func=lambda x, y: print(x, y, end="\n"), path=None):
    if path is None:  # path Default argument value is mutable
        path = []
    for key in obj.keys():
        if type(obj[key]) is dict:
            crawl(obj[key], func, path + [key])
            continue
        func(path + [key], obj[key])


def check(value, checks, name):
    def get_check_value(key, default_result):
        return checks[key] if key in checks else default_result

    # Skip validation for all optional fields
    if "optional" in checks and checks["optional"] is True:
        return value

    incorrect = False
    # Only treat empty dicts as incorrect, not empty strings
    if value == {}:
        incorrect = True
    if not incorrect and "type" in checks:
        try:
            value = eval(checks["type"])(value)
        except:
            incorrect = True

    if (
        not incorrect and "options" in checks and value not in checks["options"]
    ):  # FAILSTATE Value is not one of the options
        incorrect = True
    if (
        not incorrect
        and "regex" in checks
        and (
            (isinstance(value, str) and re.match(checks["regex"], value) is None)
            or not isinstance(value, str)
        )
    ):  # FAILSTATE Value doesn't match regex, or has regex but is not a string.
        incorrect = True

    if (
        not incorrect
        and not hasattr(value, "__iter__")
        and (
            ("nmin" in checks and checks["nmin"] is not None and value < checks["nmin"])
            or ("nmax" in checks and checks["nmax"] is not None and value > checks["nmax"])
        )
    ):
        incorrect = True
    if (
        not incorrect
        and hasattr(value, "__iter__")
        and (
            ("nmin" in checks and checks["nmin"] is not None and len(value) < checks["nmin"])
            or ("nmax" in checks and checks["nmax"] is not None and len(value) > checks["nmax"])
        )
    ):
        incorrect = True

    if incorrect:
        value = handle_input(
            message=(
                (("[blue]Example: " + str(checks["example"]) + "\n") if "example" in checks else "")
                + "[red]"
                + ("Non-optional ", "Optional ")["optional" in checks and checks["optional"] is True]
            )
            + "[#C0CAF5 bold]"
            + str(name)
            + "[#F7768E bold]=",
            extra_info=get_check_value("explanation", ""),
            check_type=eval(get_check_value("type", "False")),
            default=get_check_value("default", NotImplemented),
            match=get_check_value("regex", ""),
            err_message=get_check_value("input_error", "Incorrect input"),
            nmin=get_check_value("nmin", None),
            nmax=get_check_value("nmax", None),
            oob_error=get_check_value(
                "oob_error", "Input out of bounds(Value too high/low/long/short)"
            ),
            options=get_check_value("options", None),
            optional=get_check_value("optional", False),
        )
    return value


def crawl_and_check(obj: dict, path: list, checks: dict = {}, name=""):
    if len(path) == 0:
        return check(obj, checks, name)
    
    # Handle nested sections like "settings.background"
    if "." in path[0]:
        section, subsection = path[0].split(".")
        if section not in obj:
            obj[section] = {}
        if subsection not in obj[section]:
            obj[section][subsection] = {}
        obj[section][subsection] = crawl_and_check(obj[section][subsection], path[1:], checks, subsection)
        return obj
    else:
        if path[0] not in obj:
            obj[path[0]] = {}
        obj[path[0]] = crawl_and_check(obj[path[0]], path[1:], checks, path[0])
        return obj


def check_vars(path, checks):
    global config
    crawl_and_check(config, path, checks)


def check_toml(template_file, config_file) -> Tuple[bool, Dict]:
    global config
    try:
        template = toml.load(template_file)
    except Exception as error:
        console.print(f"[red bold]Encountered error when trying to to load {template_file}: {error}")
        return False
    try:
        loaded_config = toml.load(config_file)
        # Merge loaded config with default config
        for section in config:
            if section in loaded_config:
                if isinstance(config[section], dict):
                    for key in config[section]:
                        if key in loaded_config[section]:
                            if key == "background":
                                # Special handling for background settings
                                for bg_key in config[section][key]:
                                    if bg_key in loaded_config[section][key]:
                                        config[section][key][bg_key] = loaded_config[section][key][bg_key]
                            else:
                                config[section][key] = loaded_config[section][key]
                else:
                    config[section] = loaded_config[section]
    except toml.TomlDecodeError:
        console.print(
            f"""[blue]Couldn't read {config_file}.
Overwrite it?(y/n)"""
        )
        if not input().startswith("y"):
            print("Unable to read config, and not allowed to overwrite it. Giving up.")
            return False
        else:
            try:
                with open(config_file, "w") as f:
                    f.write("")
            except:
                console.print(
                    f"[red bold]Failed to overwrite {config_file}. Giving up.\nSuggestion: check {config_file} permissions for the user."
                )
                return False
    except FileNotFoundError:
        console.print(
            f"""[blue]Couldn't find {config_file}
Creating it now."""
        )
        try:
            with open(config_file, "x") as f:
                f.write("")
        except:
            console.print(
                f"[red bold]Failed to write to {config_file}. Giving up.\nSuggestion: check the folder's permissions for the user."
            )
            return False

    console.print(
        """\
[blue bold]###############################
#                             #
# Checking TOML configuration #
#                             #
###############################
If you see any prompts, that means that you have unset/incorrectly set variables, please input the correct values.\
"""
    )
    crawl(template, check_vars)
    with open(config_file, "w") as f:
        toml.dump(config, f)
    return config


if __name__ == "__main__":
    directory = Path().absolute()
    check_toml(f"{directory}/utils/.config.template.toml", "config.toml")
