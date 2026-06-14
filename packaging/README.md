# Packaging Notes

Esta pasta prepara o LucoaScript para futuros pacotes de distribuicao.

## Arch Linux

O arquivo `arch/PKGBUILD` e um ponto de partida para empacotar via `makepkg`.

## Outras distribuicoes

Como o projeto usa `pyproject.toml` com `setuptools`, ele tambem fica bem preparado para:

- Debian e Ubuntu via `pybuild` ou `python3 -m build`
- Fedora via macros Python modernas
- openSUSE via backend PEP 517

## Artefatos recomendados

Para distribuicao publica, gere:

```bash
python -m build
```

Isso produz `sdist` e `wheel`, que servem como base para empacotamento em varias distribuicoes.
