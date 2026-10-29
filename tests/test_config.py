"""開源版設定：金鑰只從環境變數讀、預設空值；程式裡沒有寫死的金鑰或內部主機。"""
import os
import pathlib
import re
import sqlite3
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'app'))
import integrations as ix  # noqa: E402

SOURCES = [p for p in (ROOT / 'app').rglob('*') if p.suffix in ('.py', '.js', '.html', '.css', '.sql') and '__pycache__' not in p.parts]


class SecretFromEnvTest(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(':memory:')
        self.con.execute('CREATE TABLE secrets(key TEXT PRIMARY KEY, value TEXT)')

    def tearDown(self):
        self.con.close()
        os.environ.pop('DISPATCH_SECRET_LINE_TOKEN_DEMOSHOP', None)

    def test_env_name(self):
        self.assertEqual(ix.env_secret_name('line_token_demoshop'), 'DISPATCH_SECRET_LINE_TOKEN_DEMOSHOP')
        self.assertEqual(ix.env_secret_name('linepay_channel_secret'), 'DISPATCH_SECRET_LINEPAY_CHANNEL_SECRET')

    def test_default_empty(self):
        os.environ.pop('DISPATCH_SECRET_LINE_TOKEN_DEMOSHOP', None)
        self.assertIsNone(ix.secret(self.con, 'line_token_demoshop'))

    def test_env_wins(self):
        os.environ['DISPATCH_SECRET_LINE_TOKEN_DEMOSHOP'] = 'test-token-not-real'
        self.assertEqual(ix.secret(self.con, 'line_token_demoshop'), 'test-token-not-real')

    def test_plain_fallback_roundtrip(self):
        self.assertEqual(ix.protect('plain:abc', True), 'abc')        # 非 Windows 存的內部金鑰讀得回來

    def test_blank_env_is_unset(self):
        os.environ['DISPATCH_SECRET_LINE_TOKEN_DEMOSHOP'] = '   '
        self.assertIsNone(ix.secret(self.con, 'line_token_demoshop'))


class NoHardcodedSecretsTest(unittest.TestCase):
    PATTERNS = {
        'private key': r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
        'anthropic/openai key': r'\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{30,}',
        'google key': r'\bAIza[0-9A-Za-z_\-]{30,}',
        'github token': r'\bgh[pousr]_[A-Za-z0-9]{30,}',
        'real LINE userId': r'\bU(?!0{32})[0-9a-f]{32}\b',
        'mobile number': r'(?<!\d)09(?!00|28-?880-?392)\d{2}-?\d{3}-?\d{3}(?!\d)',      # 只允許示範用的 0900-000-xxx 與作者公開的聯絡電話
        'windows user path': r'[A-Za-z]:\\\\?(?:Users|AI)',
    }

    def test_no_secret_patterns(self):
        hits = []
        for p in SOURCES:
            text = p.read_text(encoding='utf-8')
            for name, pat in self.PATTERNS.items():
                for m in re.finditer(pat, text):
                    hits.append(f'{p.relative_to(ROOT)}: {name}: {m.group(0)[:12]}')
        self.assertEqual(hits, [])

    def test_external_features_default_off(self):
        demo = (ROOT / 'app' / 'demo_server.py').read_text(encoding='utf-8')
        self.assertIn("os.environ['DISPATCH_NO_PUSH'] = '1'", demo)          # 示範一律不推播、不連 LINE／金流
        self.assertIn("os.environ['DISPATCH_AIB_LOCAL'] = '0'", demo)
        self.assertEqual(os.environ.get('DISPATCH_LOCAL_LLM_GATEWAY', ''), '')


if __name__ == '__main__':
    unittest.main()
