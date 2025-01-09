import docker
import os 
import utils_docker
import shutil 
import sys

# Initialize Docker client
DOCKER_CLIENT = docker.from_env()

# Define paths
current_dir = os.path.abspath(os.path.dirname(__file__))
container_dir = "/app"
requirements_file = "requirements.txt"
streamlit_app = "app.py"

def initializeFiles():
    envExample = os.path.join(current_dir, "env.example.py")
    envFile = os.path.join(current_dir, "env.py")
    # Check if we are in a GitHub Actions environment
    in_github_actions = os.getenv("GITHUB_ACTIONS") == "true"
    print(in_github_actions)
    
    if not os.path.isfile(envFile):
        shutil.copy(envExample, envFile)
        print("env.py file did not exist and has been created. Please edit it to update the necessary values, then re-run this script.")
        
        # Exit only if not in GitHub Actions
        if not in_github_actions:
            sys.exit(1)
        else:
            print("Running in GitHub Actions, continuing without exiting.")
initializeFiles()
import env

# Base configuration
if False: # Enable this to run Ollama
    ollama = {
        "name": "ollama",
        "detach": True,  # Runs the container in detached mode
        "volumes": {
            os.path.join(current_dir, "ollama", "ollama_models"): {
                "bind": "/root/.ollama/models",
                "mode": "rw",
            },
            os.path.join(current_dir, "ollama", "whisper_models"): {
                "bind": "/data/cache/whisper/models",
                "mode": "rw",
            },
        },
        "environment": {
            "OLLAMA_ORIGINS": "*",
            "ENABLE_OLLAMA_API": "True",
            "DATA_DIR": "/data",
        },
        "image": "ollama/ollama",
        "ports":{"11434/tcp": 11434},  # LLama (11434 in leetspeak) default port
    }
    utils_docker.run_container(ollama)


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
if env.DOCKER_NETWORK is not None:
    initiative["network"] = env.DOCKER_NETWORK

utils_docker.run_container(initiative)