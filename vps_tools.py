import subprocess

def get_xray_status():

    try:
        result = subprocess.run(
            ["systemctl", "is-active", "xray"],
            capture_output=True,
            text=True
        )

        return result.stdout.strip()

    except:
        return "unknown"