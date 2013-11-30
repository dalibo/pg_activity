class Process():
    """
    Simple class for process management.
    """
    def __init__(self, pid = None, database = None, user = None, client = None, cpu = None, mem = None, read = None, write = None, query = None, duration = None, wait = None, extras = None):
        self.pid = pid
        self.database = database
        self.user = user
        self.client = client
        self.cpu = cpu
        self.mem = mem
        self.read = read
        self.write = write
        self.query = query
        self.duration = duration
        self.wait = wait
        self.extras = extras

    def setExtra(self, key, value):
        self.extras[key] = value

    def getExtra(self, key):
        if self.extras is not None and self.extras.has_key(key):
            return self.extras[key]
