from pathlib import Path

import pdfminer.layout
import pytest


@pytest.fixture()
def pdf():
    return Path('../../../data/example.pdf')


def test_extract_fulltext(pdf):
    from modules.utils.pdf_manipulation import extract_fulltext

    assert pdf.exists() is True  # able to fine test pdf
    text: str = extract_fulltext(pdf)
    assert text.__contains__('object categorization') is True
    text = ''
    assert text.__contains__('Cats and Dogs') is False


def test_extract_elements(pdf):
    from modules.utils.pdf_manipulation import extract_elements

    elements = extract_elements(pdf)

    assert elements is not None


def test_get_element_list(pdf):
    from modules.utils.pdf_manipulation import get_element_list

    # elements = get_element_list(pdf, pdfminer.layout.LTFigure)
    elements = get_element_list(pdf)

    assert elements is not []


def test_get_string_occurrence(pdf):
    from modules.utils.pdf_manipulation import get_element_list, get_string_occurrence
    element_list = get_element_list(pdf=pdf, tag=pdfminer.layout.LTTextBox)
    count = get_string_occurrence(element_list, 'figure ')
    assert count == 7
