import blessed


BLESSED_VERSION = tuple(int(x) for x in blessed.__version__.split(".", 2)[:2])


if BLESSED_VERSION < (1, 17):

    def link(term: blessed.Terminal, url: str, text: str, url_id: str = "") -> str:
        return url


else:

    def link(term: blessed.Terminal, url: str, text: str, url_id: str = "") -> str:
        return term.link(url, text, url_id=url_id)
