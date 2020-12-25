from . import nodes
from . import compiler
from . import context


class Template:

    def __init__(self, template_string, template_id="UNIDENTIFIED"):
        self.root_node = compiler.compile(template_string, template_id)
        self.block_registry = self._register_blocks(self.root_node, {})

    def __str__(self):
        return str(self.root_node)

    def render(self, *pargs, **kwargs):
        data_dict = pargs[0] if pargs else kwargs
        return self.root_node.render(context.Context(data_dict, self))

    def _register_blocks(self, node, registry):
        if isinstance(node, nodes.BlockNode):
            registry.setdefault(node.title, []).append(node)
        for child in node.children:
            self._register_blocks(child, registry)
        return registry
