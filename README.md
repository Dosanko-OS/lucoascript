# LucoaScript CLI

LucoaScript (LS1) agora pode ser executado como uma ferramenta de linha de comando chamada `lucoa`.

## Comandos

```bash
lucoa exec hello.ls1
lucoa version
lucoa
```

Tambem funciona em modo direto:

```bash
lucoa hello.ls1
```

## Instalacao

Modo editavel:

```bash
python -m pip install -e .
```

Instalacao normal:

```bash
python -m pip install .
```

## Instalacao global com pipx

O `pipx` instala o comando em um ambiente isolado, mas deixa `lucoa` disponivel globalmente no sistema:

```bash
pipx install .
```

Atualizando uma instalacao local com `pipx`:

```bash
pipx upgrade lucoa
```

Se o `pipx` ainda nao estiver instalado:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

## Teste rapido

```bash
lucoa version
lucoa examples/hello.ls1
lucoa exec examples/hello.ls1
```

## REPL

```bash
lucoa
```

Comandos como `exit` e `quit` encerram o modo interativo.

## Empacotamento para distribuicoes

A base de empacotamento para Linux fica em `packaging/`:

- `packaging/arch/PKGBUILD`
- `packaging/README.md`

O projeto usa `pyproject.toml` com `setuptools`, o que facilita empacotar para Arch Linux, Debian, Fedora e outras distribuicoes que constroem pacotes Python a partir de um backend PEP 517.
