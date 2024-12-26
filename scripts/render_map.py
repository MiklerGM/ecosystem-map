import sys
import datetime
from typing import List, Dict, Any, Optional
import os
from ruamel.yaml import YAML

yaml = YAML()
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)

YAML_DIR = "../data"

# Mapping constants
ACTIVITY_INDICATORS = {
    "Active": "🟢 Active",
    "Moderate activity": "🟡 Moderate activity",
    "Inactive": "💤 Inactive",
    "Unknown": "",
}
STATUS_MAPPING = {
    "In research": "🔬",
    "Connected to Relay chain": "⚡️",
    "Connected to Parachain": "⚡️",
    "In development": "🚀",
    "In production": "⚡️",
    "Validated POC / testnet": "⚠️",
    "Discontinued": "💤",
}
LINK_MAPPING = {
    "contact": "Mail",
    "documentation": "Docs",
    "playstore": "Playstore",
    "appstore": "Appstore",
    "webstore": "Extension",
}


def safe_get(dictionary: Dict, keys: List[Any], default: Any = None) -> Any:
    """Safely retrieve a nested dictionary or list value."""
    res = dictionary
    for key in keys:
        if isinstance(res, dict):
            res = res.get(key, default)
        elif isinstance(res, list):
            if isinstance(key, int) and 0 <= key < len(res):
                res = res[key]
            else:
                return default
        else:
            return default
    return res


def map_activity(github_pushed_at: Optional[int]) -> str:
    """Map GitHub activity based on the last pushed date."""
    if not github_pushed_at:
        return ACTIVITY_INDICATORS["Inactive"]
    today = datetime.datetime.now()
    last_push_date = datetime.datetime.fromtimestamp(github_pushed_at)
    delta = (today - last_push_date).days
    if delta <= 30:
        return ACTIVITY_INDICATORS["Active"]
    elif delta <= 90:
        return ACTIVITY_INDICATORS["Moderate activity"]
    else:
        return ACTIVITY_INDICATORS["Inactive"]


def format_links(links: Dict[str, str]) -> str:
    """Format web links as markdown links."""
    return " \\| ".join(
        f"[{LINK_MAPPING.get(key, key.capitalize())}]({value})"
        for key, value in links.items()
        if value and key in LINK_MAPPING
    )


def format_number(value: int) -> str:
    """Format metric value to make it human readable"""
    if value < 1000:
        return str(value)
    return f"{round(value / 1000)}K"


# Table generation
def generate_markdown_table(data: List[Dict[str, Any]]) -> str:
    # Define table columns
    columns = [
        "Project Name",
        "Links",
        "Category",
        "GitHub Activity",
        "Ecosystem",
        "Description",
        "Target Audience",
        "Media Exposure",
        "GitHub",
        "Audit",
        "Treasury Funded",
    ]

    # Generate table header
    header = f"| {' | '.join(columns)} |"
    separator = f"| {' | '.join(['-' * len(col) for col in columns])} |"
    rows = []

    # Generate table rows
    for entry in data:
        name = f"[{safe_get(entry, ['name'], 'N/A')}]({safe_get(entry, ['web', 'site'], '#')})"
        links = format_links(safe_get(entry, ["web"], {}))
        category = ", ".join(safe_get(entry, ["category"], []))
        github_activity = map_activity(
            safe_get(entry, ["metrics", "github_pushed_at", 0, "value"])
        )

        ecosystem = ", ".join(safe_get(entry, ["ecosystem"], []))
        readiness = safe_get(entry, ["readiness", "technology"], None)
        if readiness is not None:
            ecosystem += f" ({STATUS_MAPPING.get(readiness, '❔')} {readiness})"

        description = (
            safe_get(entry, ["description"], "No description available")
            .replace("\n", " ")
            .replace("|", "")
        )

        audience = ", ".join(safe_get(entry, ["target_audience"], []))

        media_exposure = []
        if safe_get(entry, ["web", "twitter"], None) is not None:
            media_exposure.extend(
                [
                    f"[Twitter 🐦](https://x.com/{safe_get(entry, ['web', 'twitter'], '#')}) - ",
                    f"{format_number(safe_get(entry, ['metrics', 'twitter', 0, 'value'], 0))} followers <br> ",
                ]
            )
        if safe_get(entry, ["web", "discord"], None) is not None:
            media_exposure.extend(
                [
                    f"[Discord 🗨]({safe_get(entry, ['web', 'discord'], '#')}) - "
                    f"{format_number(safe_get(entry, ['metrics', 'discord', 0, 'value'], 0))} members"
                ]
            )
        media_exposure = " ".join(media_exposure)

        github = ""
        if safe_get(entry, ["web", "github"], None) is not None:
            value = format_number(safe_get(entry, ["metrics", "github", 0, "value"], 0))
            github = f"[GitHub]({safe_get(entry, ['web', 'github'], '#')}) ⭐️ {value}"

        audit = "✔️" if safe_get(entry, ["audit"], False) else "✖️"
        treasury_funded = "✔️" if safe_get(entry, ["treasury_funded"], False) else "✖️"

        # Assemble row
        row = [
            name,
            links,
            category,
            github_activity,
            ecosystem,
            description,
            audience,
            media_exposure,
            github,
            audit,
            treasury_funded,
        ]
        rows.append(f"| {' | '.join(row)} |")

    return "\n".join([header, separator] + rows)


def read_yaml(file_path: str) -> Dict:
    with open(file_path, "r") as file:
        data = yaml.load(file)
    return data


def process_yaml_files():
    """Process all YAML files in the directory."""
    yaml_files = sorted(
        file_name
        for file_name in os.listdir(YAML_DIR)
        if file_name.endswith((".yaml", ".yml"))
    )

    file_data = [
        read_yaml(os.path.join(YAML_DIR, file_name)) for file_name in yaml_files
    ]

    # Collect categories
    categories = set()
    for file in file_data:
        categories.update(file.get("category", []))

    categories = sorted(categories)

    # Generate tables
    tables = []
    for cat in categories:
        files_in_category = sorted(
            (f for f in file_data if cat in f.get("category", [])),
            key=lambda x: x.get("name", ""),
        )
        if not files_in_category:
            continue
        table = generate_markdown_table(files_in_category)
        tables.append(f"## Category: {cat}\n\n{table}")

    return tables


if __name__ == "__main__":
    tables = process_yaml_files()
    for table in tables:
        print(table)
        print("\n")  # Add spacing between tables
