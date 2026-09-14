# agent/core/tools.py
import requests
from langchain_core.tools import tool


from kubernetes import client, config

import subprocess
import os
from langchain_core.tools import tool