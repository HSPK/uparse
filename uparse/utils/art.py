from art import text2art


def print_uparse_text_art(suffix=None):
    font = "nancyj"
    ascii_text = "  uparse"
    if suffix:
        ascii_text += f"  x  {suffix}"
    ascii_art = text2art(ascii_text, font=font)
    print("\n")
    print(ascii_art)
    print("\n")
