"""Catalog completeness, Windows preference mapping and safe translated diagnostics."""
import json,string,sys,unittest
from pathlib import Path
from urllib.error import HTTPError,URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import localization as l10n
import engine

class Languages(unittest.TestCase):
 def tearDown(self):l10n.set_language(l10n.select_language(l10n.windows_languages()))
 def test_all_catalogs_have_every_key_and_matching_placeholders(self):
  base=l10n.read_catalog('enUS');fields=lambda text:{name for _,name,_,_ in string.Formatter().parse(text) if name}
  for code in l10n.LOCALES:
   values=l10n.read_catalog(code);self.assertEqual(set(values),set(base),code)
   for key,text in values.items():
    with self.subTest(locale=code,key=key):self.assertTrue(text.strip());self.assertEqual(fields(text),fields(base[key]));self.assertNotIn('\ufffd',text)
 def test_locale_variants_and_aliases(self):
  for tag,expected in {'en-US':'enUS','en-GB':'enUS','enGB':'enUS','es-ES':'esES','es-MX':'esMX','es-419':'esMX','es-AR':'esMX','de-CH':'deDE','fr-CA':'frFR','it-CH':'itIT','pt-PT':'ptBR','ptPT':'ptBR','ru-RU':'ruRU','ko-KR':'koKR','zh-CN':'zhCN','zh-Hans':'zhCN','zh-Hans-HK':'zhCN','zh-SG':'zhCN','zh-TW':'zhTW','zh-Hant':'zhTW','zh-HK':'zhTW'}.items():
   with self.subTest(tag=tag):self.assertEqual(l10n.normalize(tag),expected)
 def test_first_supported_windows_ui_preference_wins(self):
  self.assertEqual(l10n.select_language(['ja-JP','fr-CA','en-US']),'frFR');self.assertEqual(l10n.select_language(['es-MX','es-ES']),'esMX');self.assertEqual(l10n.select_language(['ja-JP']),'enUS');self.assertEqual(l10n.select_language([]),'enUS')
 def test_every_diagnostic_is_localized_and_never_leaks_exception_details(self):
  for code in l10n.LOCALES:
   l10n.set_language(code)
   for err in (engine.CheckError('SHARING_OFF','private local detail'),HTTPError('https://example.invalid/private',503,'secret response',{},None),URLError('private detail'),PermissionError('private folder'),ValueError('private response'),engine.SyncError('private token')):
    text=engine.describe_error(err);self.assertTrue(text.startswith('['));self.assertNotIn('private',text);self.assertNotIn('secret response',text)
   self.assertIn(l10n.tr('error_service'),engine.describe_error(HTTPError('',503,'',{},None)))
 def test_fallback_and_dynamic_format(self):
  l10n.set_language('unsupported');self.assertEqual(l10n.LANGUAGE,'enUS');self.assertIn('12:34',l10n.tr('updated',time='12:34'))

if __name__=='__main__':unittest.main()
