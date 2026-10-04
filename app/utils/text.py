import re
import html

def escape_html(text: str) -> str:
    return html.escape(text, quote=False)

def clean_and_normalize_text(text: str) -> str:
    if not text:
        return ""

    # 1. Замена гомоглифов до приведения к нижнему регистру.
    homoglyphs = {
        # Верхний регистр
        'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К',
        'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т', 'X': 'Х', 'Y': 'У',
        # Нижний регистр
        'a': 'а', 'c': 'с', 'e': 'е', 'k': 'к', 'o': 'о', 'p': 'р',
        'x': 'х', 'y': 'у',
    }
    trans_table = str.maketrans(homoglyphs)
    text = text.translate(trans_table)

    # 2. Приведение текста к нижнему регистру.
    text = text.lower()

    # 3. Удаление ссылок и команд ботов.
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'/\w+(?:@\w+)?', '', text)

    # 4. Схлопывание повторяющихся букв и символов.
    # Для схлопывания только от трёх повторений: r'(.)\1{2,}'.
    text = re.sub(r'(.)\1+', r'\1', text)

    # 5. Удаление разреженного написания.
    sparse_pattern = r'\b\w([. -/])\w(?:\1\w)+\b'

    def replace_sparse(match):
        full_match = match.group(0)
        separator = match.group(1)

        if separator == ' ' and len(full_match) <= 5:
            return full_match

        return full_match.replace(separator, '')

    text = re.sub(sparse_pattern, replace_sparse, text)

    # Финальная чистка пробелов.
    text = re.sub(r'\s+', ' ', text).strip()

    return text