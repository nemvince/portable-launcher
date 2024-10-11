### portable-launcher ###
# Written for CodeWeek 2024 in a day.
# Requires a "master server" hosting teams.json and args.json.
# The master server should also host the modpacks if the server uses them.
### author: @nemvince ###
### license: AGPL 3.0 ###

from portablemc.standard import Watcher, Context, DownloadProgressEvent, JvmLoadedEvent
from portablemc.fabric import FabricVersion
from portablemc.auth import OfflineAuthSession
from msal import PublicClientApplication
from pathlib import Path
import requests
import os
import argparse
import shutil
import tqdm
import tempfile

### ARGUMENT PARSER
parser = argparse.ArgumentParser(description="Portable Minecraft")

# Team id
parser.add_argument("-t", type=int, help="Team ID")
parser.add_argument("-m", type=str, help="Master server IP")
parser.add_argument("-d", action="store_true", help="Debug mode")
parser.add_argument("-D", action="store_true", help="Delete the existing instance")

args = parser.parse_args()

### CONSTANTS
CLIENT_ID = "client"
TENANT_ID = "tenant"
MASTER_SERVER = args.m if args.m else "0.0.0.0"
DEBUG = args.d

### UTILS
def exitGracefully():
  input("[CW]: Hiba történt. Kérlek szólj egy szervezőnek!")
  os._exit(1)

def debug(msg):
  if DEBUG:
    print(f"[DEBUG]: {msg}")

def cwPrint(msg):
  print(f"[CW]: {msg}")

### PROGRESS REPORTER
class cwWatcher(Watcher):
  def handle(self, event) -> None:
    if isinstance(event, DownloadProgressEvent):
      pass
    else:
      debug(event)
      if isinstance(event, JvmLoadedEvent):
        cwPrint("A játék hamarosan elindul...")

### MSAL
app = PublicClientApplication(
  client_id=CLIENT_ID,
  authority=f"https://login.microsoftonline.com/{TENANT_ID}"
)

cwPrint("Böngésző megnyitása...")
cwPrint("Kérlek jelentkezz be a Microsoft fiókoddal!")
result = app.acquire_token_interactive(
  ["User.Read"],
  prompt="select_account",
  port=13371,
)

try:
  userData = result["id_token_claims"]
except KeyError:
  cwPrint("Ajaj, belépési hiba történt.")
  exitGracefully()

try:
  name = userData["name"]
  email = userData["preferred_username"]
  userId = userData["oid"]

  cwPrint(f"Üdv, {name}!")
except:
  cwPrint("Az adatok lekérése sikertelen.")
  exitGracefully()

# make a minecraft username from the email
names = [x.capitalize() for x in email.split("@")[0].split(".")]
firstCharInt = ord(userId[0])

username = names[0] + names[1] + str(firstCharInt)

if len(username) > 16:
  firstTwoChars = userId[:2]
  firstTwoChars = [str(ord(x)) for x in firstTwoChars]
  username = names[0] + "".join(firstTwoChars)

username.replace("-", "")

cwPrint(f"A játékos neved: {username}")

### FETCHING FROM MASTER SERVER
cwPrint("Szerver információk lekérése...")
try:
  tResponse = requests.get(f"http://{MASTER_SERVER}/teams.json")
  aResponse = requests.get(f"http://{MASTER_SERVER}/args.json")
  tJson = tResponse.json()
  aJson = aResponse.json()
  serverPort = None
  for team in tJson["teams"]:
    if name in team["members"]:
      cwPrint(f"A csapatod: {team['name']}")
      serverPort = team["server_port"]
      break
  if serverPort is None:
    if args.t is None:
      cwPrint("Nem találtunk csapatot a fiókodhoz.")
      exitGracefully()
    for team in tJson["teams"]:
      teamId = team["name"]
      if f"({args.t})" in teamId:
        cwPrint(f"A csapatod: {team['name']}")
        serverPort = team["server_port"]
        break
except:
  cwPrint("Nem sikerült kapcsolódni a szerverhez.")
  exitGracefully()

if serverPort is None:
  cwPrint("Nem találtunk csapatot a fiókodhoz.")
  exitGracefully()

### MINECRAFT
appdata = os.getenv("APPDATA")
mcpath = Path(appdata) / ".cwmc"

tempPath = Path(tempfile.gettempdir()) / "cwmc"

# remove the temp directory if it exists
if tempPath.exists():
  shutil.rmtree(tempPath)
tempPath.mkdir()

shouldDelete = False
if not mcpath.exists():
  mcpath.mkdir()
else:
  shouldDelete = args.D or (len(list(mcpath.glob("mods/*"))) == 0 and aJson["useModpack"] or aJson["wipeOnStart"])

  if shouldDelete:
    debug("Deleting the existing instance")
    # remove the directory
    shutil.rmtree(mcpath)
    mcpath.mkdir()
  else: debug("Not deleting the existing instance")

if aJson["useModpack"] and shouldDelete == True:
  cwPrint("Modpack letöltése...")
  modpackUrl = f"http://{MASTER_SERVER}/{aJson['modpackUrl']}"
  modpackPath = tempPath / "modpack.zip"

  response = requests.get(modpackUrl, stream=True)
  total_size = int(response.headers.get('content-length', 0))
  block_size = 1024

  with tqdm.tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
    with open(modpackPath, 'wb') as file:
      for data in response.iter_content(block_size):
        pbar.update(len(data))
        file.write(data)

  if total_size != 0 and pbar.n != total_size:
    cwPrint("A modpack letöltése sikertelen.")
    exitGracefully()

  cwPrint("Modpack kicsomagolása...")
  # modpacks are exported from Prism Launcher
  # there is a directory named .minecraft in the modpack, we need to move that to the mcpath
  shutil.unpack_archive(modpackPath, tempPath)
  modpackDir = tempPath / ".minecraft"
  for item in modpackDir.glob("*"):
    shutil.move(item, mcpath)
  shutil.rmtree(tempPath)

context = Context(mcpath)
ver = FabricVersion.with_fabric("1.21.1", context=context)

ver.auth_session = OfflineAuthSession(username=username, uuid=userId)

ver.set_quick_play_multiplayer(MASTER_SERVER, serverPort)

env = ver.install(watcher=cwWatcher())

cwPrint("A szervezők jó játékot kívánnak!")

env.run()