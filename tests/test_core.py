import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from iec61850.backend import Backend, ModelItem
from iec61850.scl import load_scl

class CoreTests(unittest.TestCase):
    def test_browse_output(self):
        backend=Backend(Path("bridge.exe"))
        with patch.object(backend,"run",return_value="LD\tIED1\nLN\tIED1/LLN0\nDO\tIED1/LLN0.Mod\n"):
            self.assertEqual(backend.browse("x",102),[ModelItem("LD","IED1"),ModelItem("LN","IED1/LLN0"),ModelItem("DO","IED1/LLN0.Mod")])
    def test_scl_import(self):
        xml='''<SCL xmlns="http://www.iec.ch/61850/2003/SCL"><IED name="IED"><AccessPoint><Server><LDevice inst="LD0"><LN0 lnClass="LLN0" inst=""/><LN lnClass="MMXU" inst="1"/></LDevice></Server></AccessPoint></IED></SCL>'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.icd"; p.write_text(xml)
            items=load_scl(p)
        self.assertIn(ModelItem("LD","IEDLD0"),items)
        self.assertIn(ModelItem("LN","IEDLD0/MMXU1"),items)
    def test_missing_bridge_is_clear(self):
        with self.assertRaisesRegex(RuntimeError,"Native IEC61850-Komponente fehlt"):
            Backend(Path("missing-bridge.exe")).probe("127.0.0.1",102)

if __name__=="__main__": unittest.main()
