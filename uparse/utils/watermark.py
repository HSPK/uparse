from loguru import logger
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize


def remove_watermark(text: str) -> str:
    words = word_tokenize(text)

    # 统计词频
    fdist = FreqDist(words)
    # 找到高频词
    high_freq_words = {word: count for word, count in fdist.items() if count > 18}
    exclude_words = {
        "*",
        ".",
        ",",
        '""',
        ":",
        "#",
        "1",
        "(",
        ")",
        "{",
        "}",
        "点",
        ";",
        "|",
        "--",
        "2",
        "3",
        "4",
        "CAE",
        "\uf06c",
        "-|",
        "5",
        "%",
        "<",
        "-",
        "报告+完整模型",
        "X",
        "向",
        "Y",
        "度",
        "Z",
        "向静刚度",
        "方向",
        "≥8000",
        "最大动态",
        "mm",
        "静态",
        "动态",
        "!",
        "[",
        "]",
    }

    ignore_word = []
    for word in high_freq_words:
        if word not in exclude_words:
            ignore_word.append(word)
            text = text.replace(word, "")
    logger.info(f"清理高频词:{ignore_word}")
    # logger.info(f"清理后的文本:{text}")
    return text
