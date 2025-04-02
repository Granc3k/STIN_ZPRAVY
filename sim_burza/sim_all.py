import subprocess

def main():
    subprocess.run(["python", "sim_burza/sim_output.py"], check=True)
    subprocess.run(["python", "sim_burza/sim_ui.py"], check=True)

if __name__ == "__main__":
    main()