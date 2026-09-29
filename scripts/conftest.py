"""
conftest.py — Import resolution pentru reorganizare enterprise.
Mapeaza 'ana.*' → 'ANA_MAX/ana_kernel/*' pentru compatibilitate backward.

Strategie:
  - _AnaAliasFinder: intercepteaza orice import 'ana' / 'ana.*'
  - _AnaAliasLoader: importa modulul real (ana_kernel.*) si il inregistreaza
    in sys.modules atat sub 'ana_kernel.*' cat si sub 'ana.*'
  - _active flag: previne recursie infinita in find_spec
"""
import sys
import os
import importlib
import importlib.abc
import importlib.machinery
import importlib.util

_root = os.path.dirname(os.path.abspath(__file__))
_ana_max = os.path.join(_root, "ANA_MAX")

# ANA_MAX trebuie in sys.path ca 'import ana_kernel' sa functioneze
if _ana_max not in sys.path:
    sys.path.insert(0, _ana_max)


class _AnaAliasLoader(importlib.abc.Loader):
    """Loader care importa ana_kernel.X si il expune ca ana.X."""

    def create_module(self, spec):
        return None  # lasa Python sa creeze modulul default

    def exec_module(self, module):
        name = module.__name__                     # ex: 'ana.config.loader'
        real_name = "ana_kernel" + name[3:]        # ex: 'ana_kernel.config.loader'

        # Importa modulul real (ana_kernel.*)
        real_mod = importlib.import_module(real_name)

        # Inregistreaza modulul real si sub numele 'ana.*' in sys.modules
        sys.modules[name] = real_mod

        # Daca e pachet, transmite search locations pentru submodule
        if hasattr(real_mod, "__path__"):
            module.__path__ = real_mod.__path__
            module.__package__ = name


class _AnaAliasFinder(importlib.abc.MetaPathFinder):
    """Finder care redirectioneaza 'ana' si 'ana.*' la 'ana_kernel' si 'ana_kernel.*'."""

    _active = False  # guard anti-recursie

    def find_spec(self, fullname, path, target=None):
        if self._active:
            return None
        if fullname != "ana" and not fullname.startswith("ana."):
            return None

        real_name = "ana_kernel" + fullname[3:]  # 'ana' are 3 caractere

        # Gasim spec-ul real fara sa declansam recursie
        self._active = True
        try:
            real_spec = importlib.util.find_spec(real_name)
        except (ModuleNotFoundError, ValueError):
            real_spec = None
        finally:
            self._active = False

        if real_spec is None:
            return None

        # Construim un spec cu numele 'ana.*' dar cu loader-ul nostru alias
        is_pkg = real_spec.submodule_search_locations is not None
        spec = importlib.machinery.ModuleSpec(
            name=fullname,
            loader=_AnaAliasLoader(),
            origin=real_spec.origin,
            is_package=is_pkg,
        )
        if is_pkg:
            spec.submodule_search_locations = list(real_spec.submodule_search_locations)
        return spec


# Verificare ca ana_kernel exista inainte de a instala finder-ul
_kernel_path = os.path.join(_ana_max, "ana_kernel")
if os.path.isdir(_kernel_path) and "ana" not in sys.modules:
    sys.meta_path.insert(0, _AnaAliasFinder())

print("[conftest] Import resolver activ: ana.* -> ANA_MAX/ana_kernel/*")
