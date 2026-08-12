# Examples

These examples exercise the public 1.0 API without card-data clients or other
codec runtime dependencies.

| Path | Purpose |
| --- | --- |
| [`node/roundtrip.mjs`](node/roundtrip.mjs) | Runnable Node.js canonicalization, codec, export, resolver, and error example |
| [`php/roundtrip.php`](php/roundtrip.php) | Runnable PHP example using Composer autoloading |
| [`php/LaravelDeckController.php`](php/LaravelDeckController.php) | Illustrative Laravel HTTP adapter |
| [`python/roundtrip.py`](python/roundtrip.py) | Runnable Python example |
| [`python/fastapi_app.py`](python/fastapi_app.py) | Illustrative FastAPI HTTP adapter |
| [`dotnet/aspnet/`](dotnet/aspnet/) | Runnable ASP.NET minimal API with no third-party web packages |

The framework adapters return a stable deckstring error code and a
service-owned public message. They intentionally do not expose exception text
or stack traces.

## Verify from this repository

### Node.js

```bash
yarn install --frozen-lockfile
yarn run build
node examples/node/roundtrip.mjs
```

The self-reference import resolves the package through the same `exports` map
used by installed consumers.

### PHP

```bash
composer install
COMPOSER_AUTOLOAD="$(pwd)/vendor/autoload.php" \
  php examples/php/roundtrip.php
php -l examples/php/LaravelDeckController.php
```

In a Laravel application, install the Composer package and copy the controller
into `app/Http/Controllers`; the snippet expects Laravel's normal `Controller`
base class and routing stack.

### Python

```bash
PYTHONPATH=packages/python/src python3 examples/python/roundtrip.py
python3 -c 'from pathlib import Path; [compile(path.read_text(), str(path), "exec") for path in Path("examples/python").glob("*.py")]'
```

To run the optional FastAPI adapter in an application environment:

```bash
python3 -m pip install fastapi "uvicorn[standard]" manacost-deckstrings==1.0.0
fastapi dev examples/python/fastapi_app.py
```

FastAPI and its server are example-only dependencies; the deckstring package
does not require them.

### ASP.NET

Before `1.0.0` is available from NuGet, build a local package into an isolated
temporary source:

```bash
deckstrings_local_packages="$(mktemp -d)"
dotnet pack \
  packages/dotnet/src/ManacostLabs.Deckstrings/ManacostLabs.Deckstrings.csproj \
  --configuration Release \
  --output "$deckstrings_local_packages"
dotnet restore examples/dotnet/aspnet/DeckstringsApi.csproj \
  --source "$deckstrings_local_packages" \
  --source https://api.nuget.org/v3/index.json
dotnet build examples/dotnet/aspnet/DeckstringsApi.csproj \
  --configuration Release \
  --no-restore
dotnet run --project examples/dotnet/aspnet/DeckstringsApi.csproj \
  --configuration Release \
  --no-build
```

Once published, a normal `dotnet restore` resolves
`ManacostLabs.Deckstrings` 1.0.0 from NuGet. The web example uses only the
ASP.NET shared framework and the deckstring package.

Test the running API with:

```bash
curl --fail-with-body \
  --header 'Content-Type: application/json' \
  --data '{"deckstring":"AAEBAQcBBAMBAgMAAA=="}' \
  http://localhost:5000/deckstrings/decode
```

Use the actual URL printed by `dotnet run` if the development port differs.
