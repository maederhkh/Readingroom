"""Shared test fixtures."""
import pymupdf
import pytest


@pytest.fixture
def documents(tmp_path):
    """A one-page PDF: a header in the top strip, and one article of body text."""
    folder = tmp_path / "documents"
    folder.mkdir()
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842)          # A4, in points
    page.insert_text((40, 50), "L 1/1  Official Journal of the European Union", fontsize=9.6)
    page.insert_text((70, 200), "Article 1", fontsize=9.6)
    page.insert_text((70, 215), "Subject-matter and objectives", fontsize=9.6)
    pdf.save(folder / "Tiny Law.pdf")
    pdf.close()
    return folder
