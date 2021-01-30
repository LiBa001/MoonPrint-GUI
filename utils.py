def format_value(value, width=7):
    value = str(value).rjust(width, "0")[:width]

    if "-" in value:
        value = f"-{value.replace('-', '')}"

    return value
