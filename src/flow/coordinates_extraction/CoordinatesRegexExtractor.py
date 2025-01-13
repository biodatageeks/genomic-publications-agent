import re
from typing import List
from src.Config import Config
import logging

logger = logging.getLogger(__name__)

config = Config()
coordinates_regexes = config.load_coordinates_regexes() # TODO order in coordinates regexes file
logger.info(f'Loaded {len(coordinates_regexes)} coordinates regexes')
logger.debug(coordinates_regexes)

class CoordinatesRegexExtractor:
    @staticmethod
    def extract_coordinates(text: str) -> List[str]:
        matches = []
        for pattern in coordinates_regexes.values():
            matches.extend(re.findall(pattern, text))
        return matches
