import docker
import json
import subprocess
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Type

here = os.path.abspath(os.path.dirname(__file__))

# if colima is installed, point socket to that
colima_socket_path = f"unix://{os.path.expanduser('~')}/.colima/default/docker.sock"
if os.path.exists(colima_socket_path):
    print("Colima socket detected. Attaching to that")
    os.environ["DOCKER_HOST"] = colima_socket_path

DOCKER_CLIENT = docker.from_env()


def list_containers(show_all: bool = False) -> str:
    """List Docker containers."""
    try:
        containers = DOCKER_CLIENT.containers.list(all=show_all)

        if not containers:
            return "No containers found"

        result = "CONTAINER ID\tIMAGE\tSTATUS\tNAMES\n"
        for container in containers:
            result += f"{container.short_id}\t{container.image.tags[0] if container.image.tags else 'none'}\t{container.status}\t{container.name}\n"

        return result

    except Exception as e:
        return f"Error listing containers: {str(e)}"


def _extract_log_patterns(logs: str) -> Dict[str, Any]:
    """Analyze logs for common patterns and anomalies."""
    lines = logs.split("\n")
    analysis = {
        "total_lines": len(lines),
        "error_count": sum(1 for line in lines if "error" in line.lower()),
        "warning_count": sum(1 for line in lines if "warn" in line.lower()),
        "patterns": {},
        "timestamps": [],
    }

    # Extract timestamps if they exist
    for line in lines:
        try:
            if line and len(line) > 20:
                timestamp_str = line[:23]
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                analysis["timestamps"].append(timestamp)
        except (ValueError, IndexError):
            continue

    return analysis


def analyze_logs(
    self,
    container_name: str,
    time_range_minutes: Optional[int] = 60,
    filters: Optional[Dict[str, str]] = None,
    max_lines: Optional[int] = 1000,
) -> Dict[str, Any]:
    """Analyze logs from a specific container with pattern detection."""
    try:
        container = DOCKER_CLIENT.containers.get(container_name)

        # Get logs with timestamp
        since = datetime.utcnow() - timedelta(minutes=time_range_minutes)
        logs = container.logs(
            since=since, until=datetime.utcnow(), timestamps=True, tail=max_lines
        ).decode("utf-8")

        # Apply filters if specified
        if filters:
            filtered_logs = []
            for line in logs.split("\n"):
                if all(value.lower() in line.lower() for value in filters.values()):
                    filtered_logs.append(line)
            logs = "\n".join(filtered_logs)

        # Analyze logs
        analysis = self._extract_log_patterns(logs)

        # Add container info
        container_info = container.attrs
        analysis["container_info"] = {
            "id": container_info["Id"][:12],
            "name": container_info["Name"],
            "state": container_info["State"]["Status"],
            "created": container_info["Created"],
        }

        return {
            "success": True,
            "analysis": analysis,
            "raw_logs": logs if len(logs) < 1000 else f"{logs[:1000]}... (truncated)",
        }

    except docker.errors.NotFound:
        return {"success": False, "error": f"Container {container_name} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


from docker.errors import NotFound, APIError


def create_network(networkName):
    """Create Docker network if not exists"""
    try:
        DOCKER_CLIENT.networks.get(networkName)
        print(f"Network {networkName} already exists")
        return
    except:
        DOCKER_CLIENT.networks.create(networkName)
        print(f"Created Network {networkName}")
        return


def ensure_network(network_name):
    """Ensure the Docker network exists."""
    try:
        DOCKER_CLIENT.networks.get(network_name)
        print(f"Network {network_name} already exists.")
    except NotFound:
        DOCKER_CLIENT.networks.create(network_name)
        print(f"Network {network_name} created.")


def debug_container(config):
    print(f'\033[4;32mDebugging container {config["name"]}\033[0m')
    container_name = config["name"]

    # Get the container if it exists
    try:
        container = DOCKER_CLIENT.containers.get(container_name)
        print(f"Container {container_name} is in status '{container.status}'")

        if container.status == "running":
            print(f"Container {container_name} is already running")
            return True

        if container.status == "restarting":
            print("Stopping container")
            container.stop()

        # Remove the container if it exists but is not running
        print("Removing container")
        container.remove()
    except Exception as e:
        print(f"Container {container_name} not found or already removed")

    # Modify the configuration to use auto-remove and run in the foreground
    # config["auto_remove"] = True  # Enables --rm equivalent
    config["restart_policy"] = None  # Ensure no restart policy is set
    config["detach"] = False  # Run the container in daemon mode to get container object
    config["tty"] = True  # Allocate a pseudo-TTY for interactive logs
    config["remove"] = False  # equivalent to --rm

    # Now run it
    print("Starting container with debug configuration...")
    DOCKER_CLIENT.containers.run(**config)


def stop_container(container_name):
    try:
        container = DOCKER_CLIENT.containers.get(container_name)
        container.stop()
    except:
        print("Couldn't stop container {container_name}. Maybe its not running")

def run_container(config):
    print(f'\033[4;32mRunning container {config["name"]}\033[0m')
    container_name = config["name"]
    # Get the container
    try:
        container = DOCKER_CLIENT.containers.get(container_name)
        # Check the container status
        print(f"Container {container_name} is in status '{container.status}'")
        if container.status == "running":
            print(f"Container {container_name} is already running")
            return True
        if container.status == "restarting":
            print("Stopping container")
            container.stop()

        print("Removing")
        container.remove()
        print("Running container!")
    except:
        print(f"No container is running with name {container_name}")
    # Now run it
    print(f"Starting {container_name}")
    DOCKER_CLIENT.containers.run(**config)


def wait_for_db(network, db_url, db_user="postgres", max_attempts=30, delay=2):
    print(f"Using db_url: {db_url}")
    print(f"Waiting for the database to respond on {db_url}...")
    host, port = db_url.split(":")

    while True:
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    network,
                    "postgres:15-alpine",
                    "sh",
                    "-c",
                    f"pg_isready -h {host} -p {port} -U {db_user} >/dev/null 2>&1",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"The database is accepting connections on {db_url}!")
            break
        except subprocess.CalledProcessError:
            print(
                f"Still waiting for the database to accept connections on {db_url}..."
            )
            time.sleep(2)

def wait_for_db_localhost(db_port=5432, db_user="postgres", max_attempts=30, delay=2):
    """
    Wait for a PostgreSQL database to become available on localhost using Docker with host networking.
    
    Args:
        db_port (int): Port number where PostgreSQL is running
        db_user (str): PostgreSQL user to connect as
        max_attempts (int): Maximum number of connection attempts
        delay (int): Delay in seconds between attempts
    """
    print(f"Waiting for the database to respond on localhost:{db_port}...")
    
    attempts = 0
    while attempts < max_attempts:
        try:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network=host",
                    "postgres:15-alpine",
                    "pg_isready",
                    "-h", "localhost",
                    "-p", str(db_port),
                    "-U", db_user
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"The database is accepting connections on localhost:{db_port}!")
            break
        except subprocess.CalledProcessError:
            attempts += 1
            if attempts >= max_attempts:
                raise TimeoutError(f"Database did not become available after {max_attempts} attempts")
            print(f"Still waiting for the database to accept connections on localhost:{db_port}...")
            time.sleep(delay)
            
def wait_for_url(url, network):
    # Create and start the container
    stop_container("url_test")
    run_container(
        dict(
            image="curlimages/curl:latest",  # Use the curl-specific image
            name="url_test",
            network=network,
            #network_mode="host",  # Set the network mode to host
            environment={"TEST_URL": url},
            command=[
                "sh",
                "-c",
                """
            while ! curl -k $TEST_URL; do
                echo 'Waiting for Keycloak at' $TEST_URL
                sleep 2
            done
            echo 'Keycloak is up!'
            """,
            ],
            detach=False,
            remove=True,  # Automatically clean up the container after it stops
        )
    )

def model_exists(model_name):
    try:
        # Run the curl command
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-X", "POST",
                "http://localhost:11434/api/show",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"name": model_name}),
            ],
            capture_output=True,
            text=True,
        )
        # Parse the JSON response
        response = json.loads(result.stdout)

        # Check if the response contains the model's metadata
        if "license" in response or "modelfile" in response:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking model: {e}")
        return False

# to test a model
# curl http://localhost:11434/api/chat -d '{"model": "llama3.2", "messages": [{"role": "user", "content": "How are you?"}]}' | jq

def pullModels(models_to_pull):
    for model_name in models_to_pull:
        if not model_exists(model_name):
            print(f"Pulling model: {model_name}")
            run_container(
                dict(
                    image="curlimages/curl",
                    name="ModelPull",
                    command=[
                        "curl",
                        "-X",
                        "POST",
                        "http://localhost:11434/api/pull",
                        "-d",
                        json.dumps({"model": model_name}),
                    ],
                    network_mode="host",
                    remove=True,
                    detach=False,
                )
            )
        else:
            print(f"Model {model_name} already exists locally")

