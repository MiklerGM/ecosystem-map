import sys
import copy, os, time
from ruamel.yaml import YAML
from dataclasses import dataclass, field
from typing import Any, List, Dict
from datetime import datetime, timedelta
import requests

yaml = YAML()
yaml.default_flow_style = False
yaml.indent(mapping=2, sequence=4, offset=2)

GITHUB_TOKEN = os.environ.get('GITHUB_API_TOKEN', None)
if GITHUB_TOKEN is None:
    print("Error: Github API token is missing")
    print("Set GITHUB_API_TOKEN env variable")
    sys.exit(1)

YAML_DIR = "../data"
STALE_METRIC_DAYS=10

@dataclass
class MetricEntry:
    date: datetime.date
    value: int

    def is_older_than(self, days: int) -> bool:
        """Check if the metric date is older than the specified number of days."""
        return self.date < (datetime.now().date() - timedelta(days=days))

    def update_date(self):
        """Update the date to today's date."""
        self.date = datetime.now().date()

    def update_value(self, new_value: int):
        self.value = new_value
        self.update_date()

    @classmethod
    def from_dict(cls, data: dict):
        known_fields = {key: data[key] for key in ("date", "value") if key in data}
        return cls(**known_fields)

    def to_dict(self) -> dict:
        updated_data = {"date": self.date, "value": self.value}
        return updated_data


@dataclass
class EcosystemProject:
    file_name: str
    metrics: Dict[str, List[MetricEntry]] = field(default_factory=dict)
    _original_data: Dict[str, Any] = field(default_factory=dict, repr=False)
    touched: bool = False

    @classmethod
    def from_dict(cls, file_name: str, data: dict):
        metrics = {}
        for key, entries in data.get("metrics", {}).items():
            metrics[key] = [MetricEntry.from_dict(entries[0])] if len(entries) else []
        return cls(file_name=file_name, metrics=metrics, _original_data=data)

    def to_dict(self) -> dict:
        updated_data = copy.deepcopy(self._original_data)
        for key, entries in self.metrics.items():
            updated_data["metrics"][key] = [entry.to_dict() for entry in entries]
        return updated_data

    def get_metric(self, name: str) -> tuple[bool, str]:
        link = self._original_data.get('web', {}).get(name, "")
        flag = False
        if link:
          flag = True
          if name not in self.metrics:
              flag = True
          elif len(self.metrics[name]) and self.metrics[name][0].is_older_than(STALE_METRIC_DAYS):
              flag = True
          else:
              flag = False
        return (flag, link)
    
    def set_metric(self, name: str, value: int):
        if name not in self.metrics:
            self.metrics[name] = [MetricEntry.from_dict({ "date": datetime.now().date(), "value": value })]
        else:
            self.metrics[name][0].update_value(value)
        self.touched = True


def read_yaml(file_path: str) -> EcosystemProject:
    """Read a YAML file and return its content as a EcosystemProject object."""
    with open(file_path, "r") as file:
        data = yaml.load(file)
    return EcosystemProject.from_dict(file_path, data)

def write_yaml(data: EcosystemProject, file_path: str):
    """Write a EcosystemProject object back to a YAML file."""
    with open(file_path, "w") as file:
        yaml.dump(data.to_dict(), file)

def update_github(metrics_data: EcosystemProject):
    name = 'github'
    link_prefix = 'https://github.com/';
    [update, link] = metrics_data.get_metric(name)
    if update and link.startswith(link_prefix):
        data_link = link.replace(link_prefix, 'https://api.github.com/repos/')
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        try:
          response = requests.get(data_link, headers=headers)
          if response.status_code == 200:
            data_json = response.json()
            value = data_json.get("stargazers_count", None)
            if value is not None:
                metrics_data.set_metric(name, value)

            last_update = data_json.get("pushed_at", None)
            if last_update is not None:
                metrics_data.set_metric("github_pushed_at", int(datetime.fromisoformat(last_update).timestamp()))
        except:
            pass

def update_discord(metrics_data: EcosystemProject):
    name = 'discord'
    link_prefix = 'https://discord.com/invite/'
    [update, link] = metrics_data.get_metric(name)
    if update and link.startswith(link_prefix):
      # link: https://discord.com/invite/cE72GYcFgY
      # data: https://discord.com/api/v10/invites/cE72GYcFgY?with_counts=true&with_expiration=true
      # guild.icon = dc2b4ee9885f6ba04adbc5a80aa7dd70
      # https://cdn.discordapp.com/icons/849331368558198803/dc2b4ee9885f6ba04adbc5a80aa7dd70.webp?size=128
      data_link = link.replace(link_prefix, 'https://discord.com/api/v10/invites/') + '?with_counts=true&with_expiration=true'
      try:
          response = requests.get(data_link)
          if response.status_code == 200:
            value = response.json().get("approximate_member_count", None)
            if value is not None:
                metrics_data.set_metric(name, value)
      except:
          pass

def update_metrics(metrics_data: EcosystemProject):
    update_discord(metrics_data=metrics_data)
    update_github(metrics_data=metrics_data)

def process_yaml_files():
    """Process all YAML files in the directory."""
    for file_name in os.listdir(YAML_DIR):
        if file_name.endswith(".yaml") or file_name.endswith(".yml"):
            file_path = os.path.join(YAML_DIR, file_name)
            print(f"Processing file: {file_name}")

            # Read, update, and write back the YAML data
            metrics_data = read_yaml(file_path)
            update_metrics(metrics_data)
            if metrics_data.touched:
              write_yaml(metrics_data, file_path)
              time.sleep(1)
            sys.exit(0)

if __name__ == "__main__":
    process_yaml_files()
