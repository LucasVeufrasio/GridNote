"""Testes de leitura/gravação e do modelo. Rodar da raiz: python -m unittest discover tests"""
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gridnote.document import Document  # noqa: E402
from gridnote.fileio import Sheet, read_file, write_file  # noqa: E402
from gridnote.model import TableModel, replace_function  # noqa: E402

APP = QApplication.instance() or QApplication([])

ROWS = [["Nome", "Status", "Valor", "CPF"], ["Ana", "A", "10", "01234567890"], ["Bruno", "B", "2.5", "98765432100"], ["Caio", "A", "", "x;y"]]


class FileIOTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def roundtrip(self, fmt, meta=None):
        p = self.dir / f"t.{fmt}"
        write_file(p, fmt, [Sheet("Dados", [r[:] for r in ROWS], header=True)], meta or {})
        return read_file(p)

    def test_csv_roundtrip_keeps_quotes_and_leading_zero(self):
        loaded = self.roundtrip("csv", {"delimiter": ";"})
        self.assertEqual(loaded.sheets[0].rows, ROWS)
        self.assertEqual(loaded.meta["delimiter"], ";")

    def test_csv_detects_comma_and_cp1252(self):
        p = self.dir / "a.csv"
        p.write_bytes("nome,cidade\r\nJoão,São Paulo\r\n".encode("cp1252"))
        loaded = read_file(p)
        self.assertEqual(loaded.sheets[0].rows[1], ["João", "São Paulo"])
        self.assertEqual(loaded.meta["encoding"], "cp1252")

    def test_xlsx_roundtrip_multiple_sheets(self):
        p = self.dir / "m.xlsx"
        write_file(p, "xlsx", [Sheet("Um", [["a", "1"]]), Sheet("Dois", [["=SOMA(A1)", "007"]])])
        loaded = read_file(p)
        self.assertEqual([s.name for s in loaded.sheets], ["Um", "Dois"])
        self.assertEqual(loaded.sheets[0].rows, [["a", "1"]])
        self.assertEqual(loaded.sheets[1].rows, [["=SOMA(A1)", "007"]])  # texto continua texto

    def test_xls_roundtrip(self):
        loaded = self.roundtrip("xls")
        self.assertEqual(loaded.sheets[0].rows, ROWS)

    def test_xls_that_is_really_html(self):
        p = self.dir / "banco.xls"
        p.write_text("<html><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>x y</td></tr></table></html>", encoding="utf-8")
        self.assertEqual(read_file(p).sheets[0].rows, [["A", "B"], ["1", "x y"]])

    def test_txt_fixed_width_roundtrip(self):
        p = self.dir / "cnab.txt"
        content = "0001A  X\r\n0002B\r\n"
        p.write_bytes(content.encode("utf-8"))
        loaded = read_file(p, "char")
        rows = loaded.sheets[0].rows
        self.assertEqual(rows[0][4], "A")
        rows[1][7] = "Z"  # além do fim da linha: o buraco vira espaço
        write_file(p, "txt", [Sheet("x", rows)], loaded.meta)
        self.assertEqual(p.read_bytes().decode(), "0001A  X\r\n0002B  Z\r\n")

    def test_txt_auto_delimiter(self):
        p = self.dir / "t.txt"
        p.write_text("a|b|c\n1|2|3\n", encoding="utf-8")
        loaded = read_file(p)
        self.assertEqual(loaded.meta["txt_mode"], "|")
        self.assertEqual(loaded.sheets[0].rows[1], ["1", "2", "3"])

    def test_docx_is_valid_zip_with_table(self):
        p = self.dir / "t.docx"
        write_file(p, "docx", [Sheet("Dados", ROWS, header=True)])
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode()
        self.assertIn("<w:tbl>", xml)
        self.assertIn("01234567890", xml)

    def test_docx_rejects_too_many_columns(self):
        from gridnote.fileio import FileFormatError
        with self.assertRaises(FileFormatError):
            write_file(self.dir / "w.docx", "docx", [Sheet("x", [["a"] * 64])])

    def test_pdf_has_pages(self):
        p = self.dir / "t.pdf"
        rows = [["col"] * 12] + [[f"linha {i}"] * 12 for i in range(300)]
        write_file(p, "pdf", [Sheet("Dados", rows, header=True)])
        data = p.read_bytes()
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(data.count(b"/Type /Page\n") + data.count(b"/Type /Page\r") + data.count(b"/Type /Page "), 1)


class ModelTest(unittest.TestCase):
    def model(self):
        return TableModel([r[:] for r in ROWS], header=True)

    def test_replace_whole_column_A_to_Z_and_undo(self):
        m = self.model()
        fn = replace_function("A", "Z", whole=True, case=True, fill=False)
        changes = {(r, 1): fn(m.rows[r][1]) for r in m.visible_rows()}
        self.assertEqual(m.set_cells({k: v for k, v in changes.items() if v != m.rows[k[0]][k[1]]}), 2)
        self.assertEqual([m.rows[r][1] for r in range(1, 4)], ["Z", "B", "Z"])
        self.assertTrue(m.dirty)
        m.undo()
        self.assertFalse(m.dirty)
        self.assertEqual([m.rows[r][1] for r in range(1, 4)], ["A", "B", "A"])
        m.redo()
        self.assertTrue(m.dirty)

    def test_filter_rows_and_columns(self):
        m = self.model()
        m.set_filter("a", -1, "equals", False, "rows")
        self.assertEqual(list(m.visible_rows()), [1, 3])
        m.set_filter("567", -1, "contains", False, "cols")
        self.assertEqual(list(m.visible_cols()), [3])
        m.set_filter("B", 1, "equals", True, "cols")
        self.assertEqual(list(m.visible_rows()), [2])

    def test_structural_ops_keep_filter_and_undo(self):
        m = self.model()
        m.set_filter("A", 1, "equals", True, "rows")
        m.insert_rows(2)
        self.assertEqual(len(m.rows), 5)
        self.assertIn(2, list(m.visible_rows()))  # a linha nova aparece mesmo com filtro
        m.remove_cols([0])
        self.assertEqual(m.ncols, 3)
        m.undo()
        m.undo()
        self.assertEqual(m.rows, ROWS)
        self.assertFalse(m.dirty)

    def test_save_then_discard(self):
        m = self.model()
        m.set_cells({(1, 0): "Ana Maria"})
        m.mark_saved()
        self.assertFalse(m.dirty)
        m.set_cells({(1, 0): "Outra"})
        m.discard()
        self.assertEqual(m.rows[1][0], "Ana Maria")
        self.assertFalse(m.dirty)

    def test_resplit_by_char_saves_original_csv_text(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "f.csv"
            src.write_bytes(b"Mat;Nome\r\n0001;Ana\r\n")
            doc = Document.open(src)
            m = doc.models[0]
            self.assertTrue(m.header)  # cabeçalho detectado sozinho
            m.resplit("char")
            self.assertEqual((m.split, m.header, m.rows[1][:5]), ("char", False, ["0", "0", "0", "1", ";"]))
            m.set_cells({(1, 3): "9"})
            doc.save(0)
            self.assertEqual(src.read_bytes(), b"Mat;Nome\r\n0009;Ana\r\n")
            m.resplit(";")
            self.assertEqual(m.rows[1], ["0009", "Ana"])
            m.undo()
            self.assertEqual(m.split, "char")

    def test_filter_line_numbers_and_delete_shift_left(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "r.txt"
            lines = [f"L{i:02d}ABC{'55' if i in (3, 6, 9) else '5X'}FIM" for i in range(1, 11)]
            src.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
            doc = Document.open(src, "char")
            m = doc.models[0]
            m.set_filter("3, 6, 9", -1, "lines", False, "cols")
            self.assertEqual([r + 1 for r in m.visible_rows()], [3, 6, 9])
            # coluna 8 (índice 7) = segundo "5", só nas linhas visíveis
            m.delete_cells_shift_left([(ar, 7) for ar in m.visible_rows()])
            doc.save(0)
            out = src.read_bytes().decode("utf-8").split("\r\n")
            self.assertEqual(out[2], "L03ABC5FIM")
            self.assertEqual(out[3], "L04ABC5XFIM")  # linha não selecionada fica igual
            m.undo()
            self.assertEqual("".join(m.rows[2]), "L03ABC55FIM")

    def test_filter_char_mode_searches_whole_line(self):
        m = TableModel([list("AB55CD"), list("AB5XCD")], split="char")
        m.set_filter("55", -1, "contains", False, "cols")
        self.assertEqual(list(m.visible_rows()), [0])

    def test_document_save_as_pdf_is_export(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "a.csv"
            src.write_text("x;y\n1;2\n", encoding="utf-8")
            doc = Document.open(src)
            doc.models[0].set_cells({(1, 0): "9"})
            self.assertFalse(doc.save_as(Path(d) / "a.pdf", "pdf", {}, 0))
            self.assertTrue(doc.dirty)
            self.assertTrue(doc.save_as(Path(d) / "b.xlsx", "xlsx", {}, 0))
            self.assertFalse(doc.dirty)
            self.assertEqual(doc.fmt, "xlsx")


if __name__ == "__main__":
    unittest.main()
