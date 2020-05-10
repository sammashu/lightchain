
class ReaderHtml:

    @staticmethod
    def get_ui(html, app):
        htmlfile = open(app.ROOT_DIR + "/ui/" + html, 'r', encoding='utf-8')
        source_code = htmlfile.read()
        return source_code
