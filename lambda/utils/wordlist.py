import os

WORDLIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'wordlist.txt')

# Module scope: Lambda reuses the container between invocations, so the
# 537k-line file is read once per container instead of once per request.
_cache = None


def load():
    """Returns (words, word_list, five_letter_words)."""
    global _cache
    if _cache is None:
        with open(WORDLIST_PATH, 'r', encoding='utf-8') as f:
            word_list = tuple(w for w in f.read().split('\n') if w)
        _cache = (
            frozenset(word_list),
            word_list,
            tuple(w for w in word_list if len(w) == 5),
        )
    return _cache


def clear_cache():
    global _cache
    _cache = None
