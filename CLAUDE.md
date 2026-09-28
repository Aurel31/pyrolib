# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`pyrolib` is a Python tool library for the `Méso-NH/Blaze` atmospheric/fire coupled model. Its main job is generating the `FuelMap.nc` input file for a Méso-NH/Blaze run from a Méso-NH namelist + initialization file. It also contains FireFlux I experimental-data processing and numerical-method prototypes for the Blaze fire model.

Package layout is `src/`-based with three sub-packages: `pyrolib.fuelmap`, `pyrolib.data_processing` (FireFlux I), `pyrolib.blaze`.

## Commands

```bash
pip install -e ".[tests,lint]" # dev install (extras: tests, lint, docs, numba)
pytest                         # run all tests
pytest tests/unit/test_fuels.py::test_property_set   # single test
make test                      # same as pytest
make lint                      # ruff check + ruff format --check on src tests
make format                    # ruff format src tests
make typecheck                 # ty check (advisory)
make doc                       # sphinx build into docs/_build (deletes it first)
make build                     # sdist + wheel via python -m build
```

Tests in `tests/func/` build real fuel maps against `examples/fuel_map/` using `os.getcwd()`. `tests/conftest.py` has an autouse fixture that chdirs to pytest's `rootpath` (anchored on `pyproject.toml`), so pytest works from any directory — but the tests still write and delete `FuelMap.nc` / `FuelMap.des` / `FuelMap2d.nc` inside `examples/fuel_map/`, and a crashed run leaves those behind.

CI (`.github/workflows/python-package.yml`) has four jobs: `lint` (`ruff check` and `ruff format --check` on `src tests` as hard failures, then `ty check` as `continue-on-error`), `test` (pytest on Python 3.10–3.13), `docs` (`sphinx -b html -W`, so doc warnings fail CI rather than the published site), and `build` (`python -m build`, `twine check --strict`, plus a grep asserting the wheel contains `data/fuel_db/*.yml`). Ruff and ty config live in `pyproject.toml` (line-length 110); their versions are pinned in the `lint` extra, so bump them there deliberately. `fuels.py` property tables are aligned by hand, guarded with `# fmt: off` / `# fmt: on` and exempt from `E501`. The whole-repo `ruff format` commit is listed in `.git-blame-ignore-revs`.

The code base is ruff-clean and ruff-formatted, and CI keeps it that way. ty is advisory: its remaining diagnostics (about 20) are mostly attributes initialised to `None` in `__init__` and `LinePatch`-only attributes read through a `DataPatch`. They go away as the code is annotated, not with suppressions. The `BalbiFuel` imports in `fuel_database.py` and `fuelmap.py` look unused but feed the by-name class lookup, hence their `noqa: F401`.

## Architecture

### Fuel properties → netCDF slots

`fuelmap/fuels.py` is the center of the design. A `FuelProperty` holds name/value/unit/description plus a `propertyindex`. That index is **the position of the property in `FuelMap.nc`** and must stay compliant with the Blaze reader in the Fortran source; a property with `propertyindex=None` (e.g. `wind`, `slope`) exists in Python but is never written to file. `get_property_vector()` builds `[fuel_index, *values]`, so slot 0 is always the fuel type index and slots 1..N follow `propertyindex`.

Fuel classes (`BalbiFuel`, subclass of the abstract `BaseFuel`) bundle the properties of one rate-of-spread parameterization and implement `getR()` (rate of spread) and `copy()`.

Two module-level registers at the bottom of `fuels.py` bind the Méso-NH namelist to Python:

```python
_ROSMODEL_NB_PROPERTIES     = {"SANTONI2011": 22}          # array size incl. fuel index
_ROSMODEL_FUELCLASS_REGISTER = {"SANTONI2011": "BalbiFuel"} # CPROPAG_MODEL -> class name
```

Adding a new ROS parameterization means: new `BaseFuel` subclass with `propertyindex` values matching Blaze, an entry in both registers, and an update to `show_fuel_classes()`. Class lookup is done by name via `getattr(sys.modules[__name__], ...)`, so new fuel classes must be importable in the module doing the lookup (`fuels.py`, `fuel_database.py`, `fuelmap.py`).

### FuelDatabase

`FuelDatabase` is a two-level dict: `db["<dbname>_<fuel_description>"]["<FuelClassName>"] -> fuel object` (e.g. `"FireFluxI_tall_grass"` → `{"BalbiFuel": BalbiFuel(...)}`). Databases are YAML files in `src/pyrolib/data/fuel_db/` (shipped via `[tool.setuptools.package-data]`, loaded with `importlib.resources.files`) or `.yml` files in the current directory — **a local file with the same name shadows the packaged one**. YAML has two layouts selected by the `is_compact` key: compact stores bare values, non-compact stores `{Value, Unit, Description}` per property. A valid local database file needs the keys `infos`, `is_compact`, `fuels`.

### FuelMap generation pipeline

`FuelMap.__init__(fuel_db, namelistname="EXSEG1.nam", MesoNHversion="6.1.0", workdir="")`:

1. Reads defaults from `data/Default_MNH_namelist.yml`, keyed by `f"v{version.replace('.', '')}"` (`v544`, `v550`, `v560`, `v610`). Supporting a new Méso-NH version starts with a new key here; values must mirror `default_desfmn.f90`.
2. Overrides them from the namelist via `f90nml`: `nam_lunitn/cinifile`, `nam_firen/{cpropag_model,nrefinx,nrefiny}`.
3. Opens `<cinifile>.nc` for `XHAT`/`YHAT` (atmospheric grid) and optional conformal-projection variables (`BETA`, `RPK`, `LATORI`, `LONORI`, `LAT0`, `LON0`); when present, patch positions may be given in lon/lat (`is_cartesian=False`) and converted by `utility.convert_lon_lat_to_x_y` (Mercator without rotation only — anything else raises `NotImplementedError`).
4. Allocates `fuelmaparray (nbproperties, nyf, nxf)`, `ignitionmaparray` (init `1e6`), `walkingignitionmaparray` (init `-1`) on the refined fire grid `(nx*nrefinx, ny*nrefiny)`.

Then `add_*_{rectangle,line}_patch(...)` methods build a `DataPatch` (`patch.py`: `RectanglePatch`, or `LinePatch` using Bresenham) whose `datamask` is applied by the private `__assign_data_to_data_array`. That method handles four mutually exclusive data kinds: fuel properties, walking ignition (linearly interpolated along a line), ignition time, and unburnable (all properties zeroed). Fuel indices are assigned lazily, in first-use order, into `fuel_index_correspondance` and reported at dump time.

`dump_mesonh()` copies `<cinifile>.des` → `FuelMap.des` and writes `FuelMap.nc` with MesoNH netCDF conventions (dimensions `X`, `Y`, `F`, `size3`, `char16`; `FILETYPE = "BlazeData"`). `dump()` writes the human-readable `FuelMap2d.nc` with the same content in 2D. Both are needed by the tests; only `FuelMap.nc`/`.des` are needed by Méso-NH.

Version metadata is written twice on purpose: since Méso-NH 6.0.0 `IO_Mnhversion_get` reads the global attribute `MNH_VERSION` first, and only falls back to the legacy `MNHVERSION` variable, then to `MASDEV`/`BUGFIX`. `MASDEV` is *not* the major version — the reader decodes it as `major*10 + minor` (or `major*100 + minor` for minor ≥ 10), so Méso-NH 5.6.0 files carry `MASDEV = 56`. All these integers must be `np.int32`, matching the file's own `MNH_INT = "4"` attribute.

### The 2D↔3D fire-array convention

Méso-NH stores fire fields as `(Nx, Ny, Γx*Γy)` for I/O reasons even though they are 2D fields of size `(Nx*Γx, Ny*Γy)`. `utility.fire_array_2d_to_3d` / `fire_array_3d_to_2d` implement that packing and are used both when writing `FuelMap.nc` and by the `pyrolib-post rearrange-netcdf` CLI when unpacking model output. Any new fire field added to output post-processing must also be added to `LIST_FIRE_FIELD` in `cli_post.py` (`FMPHI`, `FMBMAP`, `FMROS0`, `FMROS`, `FMASE`, `FMAWC`, `FMFLUXHDH`, `FMFLUXHDW` — these names changed in 0.4.1, see CHANGELOG).

`numba` is an optional accelerator: `utility.njit_wrapper` applies `@njit` when numba is importable and is a no-op otherwise (with a warning printed at import). Functions decorated with it must stay numba-nopython-compatible.

### CLI

Two `click` groups declared as console scripts in `pyproject.toml`: `pyrolib-fm` (`cli_fuelmap.py`: `list-fuel-classes`, `list-fuel-databases`) and `pyrolib-post` (`cli_post.py`: `rearrange-netcdf`). Both use the `add_version` decorator that injects `__version__` into the group help text.

## Conventions

- Version lives only in `src/pyrolib/__init__.py` (`__version__`); `pyproject.toml` reads it with `[tool.setuptools.dynamic] version = {attr = ...}`, resolved statically by AST so the build never imports numpy. Bumping it means also adding a CHANGELOG entry (Keep a Changelog format, dated `YYYY / MM / DD`).
- The README states the supported Méso-NH range; update it alongside `Default_MNH_namelist.yml` when compliance changes.
- Docstrings are NumPy-style and consumed by Sphinx autodoc (`docs/api/*.rst`, published to ReadTheDocs). Prose docs live in `docs/howto/` as Markdown via `myst-parser`.
- Runnable examples in `examples/` double as documentation; `examples/fuel_map/` holds the Méso-NH fixtures (`EXSEG1.nam`, `Init_file.nc`, `Init_file.des`) that the functional tests depend on — don't move them.
