INVALID_INPUT = 1
DOCKER_ERROR = 2

class DkrException(Exception):
    def __init__(self, message, exit_code):
        self.message = message
        self.exit_code = exit_code