import docker
import os 
import utils_docker
import shutil 
import sys
from dotenv import load_dotenv

# Initialize Docker client
DOCKER_CLIENT = docker.from_env()

# Define paths
current_dir = os.path.abspath(os.path.dirname(__file__))
container_dir = "/app"
requirements_file = "requirements.txt"
streamlit_app = "app.py"

if not os.getenv("GITHUB_ACTIONS"):
    load_dotenv('.env', override=True)

# Run the app in a Docker container
initiative = dict(
    image="python:3.12-slim",
    name="initiative",
    command=f"sh -c 'apt-get update && apt-get install -y poppler-utils && pip install -r {requirements_file} && streamlit run {streamlit_app}'",
    volumes={
        current_dir: {
            "bind": container_dir,
            "mode": "rw",
        }
    },
    working_dir=container_dir,
    ports={"8501/tcp": 8501},  # Streamlit default port
    detach=True,
)
if os.getenv("DOCKER_NETWORK"):
    initiative["network"] = os.getenv("DOCKER_NETWORK")

utils_docker.run_container(initiative)
