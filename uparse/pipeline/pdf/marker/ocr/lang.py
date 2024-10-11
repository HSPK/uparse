from typing import List

from surya.languages import CODE_TO_LANGUAGE, LANGUAGE_TO_CODE
from surya.model.recognition.tokenizer import _tokenize as lang_tokenize

from .tesseract import LANGUAGE_TO_TESSERACT_CODE, TESSERACT_CODE_TO_LANGUAGE


def langs_to_ids(langs: List[str]):
    unique_langs = list(set(langs))
    _, lang_tokens = lang_tokenize("", unique_langs)
    return lang_tokens


def replace_langs_with_codes(
    langs, ocr_engine: str = "surya", default_langs: list[str] = ["Chinese", "English"]
):
    if ocr_engine == "surya":
        if langs is None:
            return
        for i, lang in enumerate(langs):
            if lang.title() in LANGUAGE_TO_CODE:
                langs[i] = LANGUAGE_TO_CODE[lang.title()]
    else:
        if langs is None:
            langs = default_langs
            print(f"No languages specified for tesseract, defaulting to {default_langs}.")

        for i, lang in enumerate(langs):
            if lang in LANGUAGE_TO_CODE:
                langs[i] = LANGUAGE_TO_TESSERACT_CODE[lang]
    return langs


def validate_langs(langs, ocr_engine: str = "surya"):
    if ocr_engine == "surya":
        if langs is None:
            return
        for lang in langs:
            if lang not in CODE_TO_LANGUAGE:
                raise ValueError(f"Invalid language code {lang} for Surya OCR")
    else:
        for lang in langs:
            if lang not in TESSERACT_CODE_TO_LANGUAGE:
                raise ValueError(f"Invalid language code {lang} for Tesseract")
