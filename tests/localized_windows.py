"""Check actual Tk window layout in all catalogs with synthetic account choices."""
import gc,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,localization as l10n
class Store:
 def read(self):return {'schema':1,'profiles':{},'enabled':False}
 def write(self,value):raise AssertionError('No settings writes')
profiles=[{'saved':str(Path('fixture')/'WTF'/'Account'/name/'SavedVariables'/'DeathAtlas.lua'),'addon':str(Path('fixture')/'Interface'/'AddOns'/'DeathAtlas')} for name in ('FIRST','SECOND')]
with patch.object(app.App,'tray'),patch.object(app.App,'loop'),patch.object(app.engine,'discover',return_value=[]):
 for code in l10n.LOCALES:
  l10n.set_language(code);root=app.tk.Tk();root.withdraw();ui=app.App(root,Store(),app.engine.DEFAULT_SERVICE)
  try:
   ui.scan_generation+=1;ui.set_candidates(profiles);root.deiconify();root.update();ui.fit_window();root.update()
   assert root.winfo_height()>=ui.panel.winfo_reqheight(),(code,'height',root.winfo_height(),ui.panel.winfo_reqheight())
   assert root.winfo_width()>=ui.panel.winfo_reqwidth(),(code,'width')
   assert ui.startup_checkbox.cget('text')==l10n.tr('autostart')
   assert not ui.autostart.get();assert app.tray_labels()==tuple(l10n.tr(k) for k in ('configure','about','close'))
   ui.about();root.update()
  finally:ui.close();ui=None;root=None;gc.collect()
l10n.set_language(l10n.select_language(l10n.windows_languages()))
print('PASS 11 real Tk locale layouts, startup label/default, account choices and About; no network or real settings writes')
