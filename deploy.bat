@echo off
REM ========================================
REM Script de Deploy - Velox Framework
REM ========================================

echo.
echo ========================================
echo   Velox Framework - Deploy
echo ========================================
echo.

REM Pedir a nova versão
set /p VERSION="Digite a nova versao (ex: 1.0.3): "

REM Verificar se a versão foi informada
if "%VERSION%"=="" (
    echo ERRO: Versao nao informada!
    exit /b 1
)

echo.
echo Atualizando versao no pyproject.toml...

REM Atualizar versão no pyproject.toml
python -c "
import re
with open('pyproject.toml', 'r', encoding='utf-8') as f:
    content = f.read()
content = re.sub(r'version = \"[0-9.]+\"', f'version = \"%VERSION%\"', content)
with open('pyproject.toml', 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Versao atualizada para %VERSION%')
"

echo.
echo Adicionando arquivos ao git...
git add -A

echo.
set /p COMMIT_MSG="Digite a mensagem do commit: "

if "%COMMIT_MSG%"=="" (
    set COMMIT_MSG=update: nova versao %VERSION%
)

echo.
echo Fazendo commit...
git commit -m "%COMMIT_MSG%"

echo.
echo Criando tag v%VERSION%...
git tag v%VERSION%

echo.
echo Enviando para o GitHub...
git push origin master --tags

echo.
echo ========================================
echo   Build e Publicacao no PyPI
echo ========================================
echo.

echo Limpando dist antiga...
if exist dist rmdir /s /q dist

echo.
echo Criando pacote...
python -m build

echo.
echo Publicando no PyPI...
python -m twine upload dist\velox_web-%VERSION%-py3-none-any.whl --username __token__ --password %PYPI_TOKEN%

echo.
echo ========================================
echo   Deploy Concluido!
echo ========================================
echo.
echo Versao %VERSION% publicada no PyPI!
echo Verifique em: https://pypi.org/project/velox-web/
echo.

pause
