import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from ouman_eh203.cli import main

FACTORY=Path(__file__).parent/'fixtures'/'eh203_215'/'factory_reset_pass1.json'

class MetadataCliTests(unittest.TestCase):
    def run_json(self,args):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(args),0)
        return json.loads(out.getvalue())

    def test_all_metadata(self):
        report=self.run_json(['metadata','--lang','en'])
        self.assertEqual(len(report['fields']),82)
        self.assertTrue(report['read_only'])

    def test_localized_key(self):
        for lang in ('fi','en'):
            report=self.run_json(['metadata','--lang',lang,'--key','l1_supply_min'])
            row=report['fields']['l1_supply_min']
            self.assertEqual(row['display_label'],row['label'][lang])
            self.assertEqual(row['protocol']['id'],12)

    def test_compare(self):
        report=self.run_json(['compare-defaults','--source',str(FACTORY),'--confirm-factory-reset'])
        self.assertEqual(sum(report['counts'].values()),82)

    def test_no_confirmation(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
            main(['compare-defaults','--source',str(FACTORY)])
        self.assertEqual(exc.exception.code,1)

    def test_output_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'metadata.json'
            args=['metadata','--output',str(p)]
            self.assertEqual(main(args),0)
            original=p.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(args)
            self.assertEqual(p.read_bytes(),original)
