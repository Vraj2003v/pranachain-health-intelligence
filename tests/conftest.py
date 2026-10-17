import os
import tempfile

# Use a throw-away database for tests; must be set before api.main is imported.
os.environ["PRANAPULSE_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
