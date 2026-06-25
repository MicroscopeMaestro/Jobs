tell application "Finder" to set SCRIPT_DIR to POSIX path of ((container of (path to me)) as text)
do shell script "cd " & quoted form of SCRIPT_DIR & " && export PATH='/usr/local/texlive/2025/bin/universal-darwin:$PATH' && ./launch.sh > /dev/null 2>&1 &"
