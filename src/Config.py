import os
import yaml
import json


class Config:
    def __init__(self):
        self.config = Config.load_config()

    @staticmethod
    def load_config():
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
        with open(config_path, "r") as file:
            return yaml.safe_load(file)

    def load_genomic_coordinates_examples(self):
        file_path = os.path.join(self.config['base_dir'], self.config['paths']['coordinates_extraction_examples'])
        with open(file_path, 'r') as file:
            return file.read()

    def load_coordinates_regexes(self):
        file_path = os.path.join(self.config['base_dir'], self.config['paths']['coordinates_regexes'])
        with open(file_path, 'r') as file:
            return json.load(file)
