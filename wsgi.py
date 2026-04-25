import sys
import os

project_home = '/home/jamirmulani/event_manager_pro_v1'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
