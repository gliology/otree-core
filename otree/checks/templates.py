import io

from django.utils.encoding import force_text


def has_valid_encoding(file_name):
    try:
        # need to open the file with an explicit encoding='utf8'
        # otherwise Windows may use another encoding if.
        # io.open provides the encoding= arg and is Py2/Py3 compatible
        with io.open(file_name, 'r', encoding='utf8') as f:
            template_string = f.read()
        force_text(template_string)
    except UnicodeDecodeError:
        return False
    return True
