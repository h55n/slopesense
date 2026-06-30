import os
import sys

# Add the project root to sys.path so that 'backend' module is resolvable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from backend.api.main import app
