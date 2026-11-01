"""WoW detection remains fail-closed and requests no child console on Windows."""
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import deathatlas

class ProcessVisibility(unittest.TestCase):
 def test_hidden_detection_preserves_running_game_guard(self):
  for name in ('WoW.exe','WoWClassic.exe','WoWForever.exe'):
   with self.subTest(name=name), patch.object(deathatlas.subprocess,'run',return_value=SimpleNamespace(stdout=f'"{name}","123"\n')) as run:
    self.assertTrue(deathatlas.wow_running())
    self.assertEqual(run.call_args.kwargs['creationflags'],subprocess.CREATE_NO_WINDOW)
    self.assertTrue(run.call_args.kwargs['check'])

 def test_no_game(self):
  with patch.object(deathatlas.subprocess,'run',return_value=SimpleNamespace(stdout='"explorer.exe","123"\n')):
   self.assertFalse(deathatlas.wow_running())

 def test_failure_does_not_claim_game_closed(self):
  with patch.object(deathatlas.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'tasklist')):
   with self.assertRaises(subprocess.CalledProcessError):deathatlas.wow_running()

if __name__=='__main__':unittest.main()
