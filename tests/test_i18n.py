# copyright by berlonak
# telegram: @Kilax123
"""Every UI string key must exist in both the Russian and the English dictionary."""
import re
from pathlib import Path

STATIC = Path(__file__).parents[1] / 'tgarchive' / 'static'


def dictionary_keys(source: str, lang: str) -> set[str]:
    start = source.index(f'  {lang}: {{')
    end = source.index('\n  },', start)
    return set(re.findall(r"'([a-zA-Z]+(?:\.[a-zA-Z]+)*)':", source[start:end]))


def test_translation_keys_are_complete():
    i18n = (STATIC / 'i18n.js').read_text(encoding='utf-8')
    ru, en = dictionary_keys(i18n, 'ru'), dictionary_keys(i18n, 'en')
    assert ru and ru == en, (sorted(ru - en), sorted(en - ru))
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    used = set(re.findall(r'data-i18n(?:-placeholder|-title|-aria)?="([^"]+)"', html))
    app = (STATIC / 'app.js').read_text(encoding='utf-8')
    used |= set(re.findall(r"\btn?\('([^']+)'\s*[,)]", app))
    used |= {'kind.' + k for k in ('channels', 'groups', 'saved', 'personal', 'other')}
    assert used - ru == set()


def test_no_hardcoded_russian_in_app_script():
    app = (STATIC / 'app.js').read_text(encoding='utf-8')
    assert not re.search('[А-Яа-яЁё]', app)


def test_i18n_script_loads_before_app():
    html = (STATIC / 'index.html').read_text(encoding='utf-8')
    assert html.index('/assets/i18n.js') < html.index('/assets/app.js')
