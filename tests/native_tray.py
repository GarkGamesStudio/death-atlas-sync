"""Short native Windows tray smoke test; no network or real settings."""
import sys,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
class Store:
 def read(self):return {'schema':1,'profiles':{},'enabled':False}
 def write(self,state):raise AssertionError('No real settings changes')
root=app.tk.Tk();root.withdraw()
with patch.object(app.App,'loop'),patch.object(app.engine,'discover',return_value=[]):
 ui=app.App(root,Store(),app.engine.DEFAULT_SERVICE)
 try:
  until=time.monotonic()+5
  while not ui.tray_ready.is_set() and time.monotonic()<until:root.update();time.sleep(.02)
  assert ui.tray_ready.is_set() and ui.icon and ui.icon.visible,'Windows tray icon must be visible'
  items=list(ui.icon.menu.items);assert tuple(item.text for item in items)==app.tray_labels()
  for item,expected in zip(items,('configure','about','exit')):
   while not ui.messages.empty():ui.messages.get_nowait()
   item(ui.icon);assert ui.messages.get(timeout=1)[0]==expected
 finally:ui.close()
print('PASS native Windows tray created, three menu items inspected and icon removed; no real profile/network changes')
