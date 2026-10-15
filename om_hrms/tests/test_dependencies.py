import os
import re

from odoo.modules.module import get_manifest, get_module_path
from odoo.tests import TransactionCase, tagged

# the attributes naming the records of other modules in the data files
REFERENCE = re.compile(r'''(?:ref|parent|inherit_id|groups|action|model_id|res_model_id)="([^"]+)"|%\(([a-z0-9_]+)\.''')


@tagged('post_install', '-at_install')
class TestDependencies(TransactionCase):

    def test_references_are_dependencies(self):
        """ Every module of the suite depends on the modules whose records its data files name, directly for the
            modules of the suite: a menu under My HR needs om_hr_base, even when another dependency installs it. """
        Module = self.env['ir.module.module']
        installed = {module.name: module for module in Module.search([('state', '=', 'installed')])}
        problems = []
        for name, module in installed.items():
            if not name.startswith('om_'):
                continue
            direct = set(get_manifest(name).get('depends', []))
            closure, todo = set(), [module]
            while todo:
                current = todo.pop()
                for dependency in current.dependencies_id:
                    if dependency.name not in closure:
                        closure.add(dependency.name)
                        if dependency.depend_id:
                            todo.append(dependency.depend_id)
            path = get_module_path(name)
            manifest = get_manifest(name)
            for data_file in list(manifest.get('data', [])) + list(manifest.get('demo', [])):
                if not data_file.endswith('.xml'):
                    continue
                with open(os.path.join(path, data_file)) as handle:
                    text = handle.read()
                for match in REFERENCE.finditer(text):
                    for value in filter(None, match.groups()):
                        for xmlid in value.split(','):
                            other = xmlid.strip().lstrip('!').split('.')[0] if '.' in xmlid else None
                            # the modules of the suite name the suite modules they use directly, not through
                            # another one; any other module is at least a dependency of a dependency
                            needed = direct if other and other.startswith('om_') else closure
                            if other and other != name and other in installed and other not in needed:
                                problems.append('%s (%s) names %s' % (name, data_file, xmlid.strip()))
        self.assertFalse(sorted(set(problems)), 'references to modules that are not dependencies')
