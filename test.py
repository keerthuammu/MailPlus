import subprocess

def test_command(cmd_args):
    try:
        res = subprocess.run(cmd_args, capture_output=True, text=True)
        return f"SUCCESS: stdout={res.stdout}, stderr={res.stderr}"
    except Exception as e:
        return f"ERROR: {str(e)}"

output = []
output.append("Testing 'ssh -V':")
output.append(test_command(['ssh', '-V']))
output.append("Testing 'node -v':")
output.append(test_command(['node', '-v']))
output.append("Testing 'npm -v':")
output.append(test_command(['npm', '-v']))
output.append("Testing 'ngrok version':")
output.append(test_command(['ngrok', 'version']))

with open('test_out.txt', 'w') as f:
    f.write('\n'.join(output))
