@echo off
setlocal
if not exist vendor\libiec61850 git clone --depth 1 --branch v1.6.2.1 https://github.com/mz-automation/libiec61850.git vendor\libiec61850
echo Fuer TLS muss mbedTLS 3.6.x unter vendor\libiec61850\third_party\mbedtls\mbedtls-3.6.0 liegen.
echo Fuer GOOSE muss das Npcap SDK nach vendor\libiec61850\third_party\winpcap kopiert werden.
cmake -S . -B build -A x64 -DBUILD_EXAMPLES=OFF -DBUILD_TESTS=OFF || exit /b 1
cmake --build build --config Release --target iec61850-bridge || exit /b 1
py -m pip install -r requirements-build.txt || exit /b 1
py -m unittest discover -s tests -v || exit /b 1
py -m PyInstaller --clean --noconfirm IEC61850-Reader.spec || exit /b 1
echo Fertig: dist\IEC61850-Reader.exe
