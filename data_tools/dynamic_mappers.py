import re


def cbs_age_group_rename_transform(row_value):
    # return "95+" if "of ouder" in row_value else re.sub(r'(\d+) tot (\d+) jaar', r'\1-\2', row_value)
    if "of ouder" in row_value:
        return re.sub(r'(\d+) jaar of ouder', r'\1+', row_value)
    elif "jonger dan" in row_value.lower():
        return re.sub(r'jonger dan (\d+) jaar', r'<\1', row_value, flags=re.IGNORECASE)
    elif "tot" in row_value:
        return re.sub(r'(\d+) tot (\d+) jaar', r'\1-\2', row_value)
    else:
        return re.sub(r'(\d+) jaar', r'\1', row_value)
