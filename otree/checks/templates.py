from django.template.library import InclusionNode
from django.template.loader_tags import ExtendsNode, BlockNode
from django.utils.encoding import force_text
import io

from otree.templatetags.otree import NEXT_BUTTON_TEMPLATE_PATH




class TemplateCheckNextButton(object):
    def __init__(self, root):
        self.root = root

    def get_next_button_nodes(self, root):
        nodes = []
        for node in root.nodelist:
            if isinstance(node, (ExtendsNode, BlockNode)):
                new_child_nodes = self.get_next_button_nodes(node)
                nodes.extend(new_child_nodes)
            elif isinstance(node, InclusionNode) and node.filename == NEXT_BUTTON_TEMPLATE_PATH:
                nodes.append(node)
        return nodes

    def check_next_button(self):
        next_button_nodes = self.get_next_button_nodes(self.root)
        return len(next_button_nodes) > 0


def check_next_button(root):
    check = TemplateCheckNextButton(root)
    return check.check_next_button()


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

