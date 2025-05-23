import json
import logging
import sys
from typing import MutableMapping


class Logger(object):
    def __init__(self, name: str, debug=False):
        level = logging.DEBUG if debug else logging.INFO
        self.logging = logging.getLogger(name)

        # if logger already exists don't add handlers
        if len(self.logging.handlers):
            self.logging.handlers[0].setLevel(level)
            return

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        handler.setLevel(level)

        self.logging.addHandler(handler)
        self.logging.setLevel(level)

    def log_request(
        self,
        endpoint: str,
        response: dict,
        params: dict | None = None,
        headers: dict | MutableMapping[str, str | bytes] | None = None,
    ):
        log = f"ESPN API Request: url: {endpoint} params: {params} headers: {headers} \nESPN API Response: {json.dumps(response)}"
        self.logging.debug(log)


# def setup_logger(debug=False) -> logging:
#     '''Setups Debug Logger'''
#     level = logging.DEBUG if debug else logging.INFO
#     logger = logging.getLogger('League')

#     handler = logging.StreamHandler(sys.stdout)
#     formatter = logging.Formatter('%(message)s')
#     handler.setFormatter(formatter)
#     handler.setLevel(level)

#     logger.addHandler(handler)
#     logger.setLevel(level)
#     return logger
