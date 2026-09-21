# hawk-osh
OSH node to monitor Hawk camper battery, propane and other status levels

This repo is only the build node: it holds the Gradle build, node config and launch scripts. All
code lives in the submodules under `include/`.

| Path | What |
| --- | --- |
| `include/osh-core` | [osh-core](https://github.com/opensensorhub/osh-core), pulled in as a Gradle composite build |
| `include/osh-addons` | [osh-addons](https://github.com/opensensorhub/osh-addons), where the drivers are developed and built from |
| `settings.gradle` | `addonModules`, the list of osh-addons modules built into this node |
| `dist/config` | `config.json` and `logback.xml` shipped with the node |
| `dist/scripts` | launch scripts shipped with the node |
| `tools/sensorhub-test` | runs the node in place for debugging, never packaged |

## Requirements

- JDK 17
- Gradle comes from the wrapper (8.10.2, same as osh-core and osh-addons)

## Clone

```sh
git clone --recurse-submodules git@github.com:drewbotts/hawk-osh.git
```

If already cloned without submodules:

```sh
git submodule update --init --recursive
```

## Build

```sh
./gradlew installDist    # unpacked node in build/install/hawk-osh
./gradlew distZip        # build/distributions/hawk-osh-<version>.zip
```

Neither task runs tests. `./gradlew build` does, for every included module.

## Run

```sh
cd build/install/hawk-osh
./launch.sh
```

- Admin UI: http://localhost:8181/sensorhub/admin (`admin` / `admin`, change it in `config/config.json`
  before putting the node on a shared network)
- Connected Systems API: http://localhost:8181/sensorhub/api

Observations are stored in `hawk.db` next to the launch script.

## Adding a driver

Drivers are written in `include/osh-addons`, under the matching `sensors/<category>/` folder.

1. Create or check out the driver in `include/osh-addons` (work on a branch there, the submodule
   is left on a detached HEAD after a fresh clone).
2. Add its folder name to `addonModules` in `settings.gradle`. Modules are found by name, so the
   path doesn't matter. If the driver depends on another addon through `project(':...')`, list
   that one too.
3. `./gradlew installDist`

Nothing else needs editing: `build.gradle` and `tools/sensorhub-test` both pick up every module in
`addonModules`.

`sensorhub-driver-fakeweather` is only in the list to smoke-test the node and can be removed once a
real driver is in.

## Debugging a driver

```sh
./gradlew :sensorhub-test:run
```

or run `TestSensorHub` from the IDE with the repo root as working directory. This uses
`tools/sensorhub-test/src/main/resources/config.json`, which is the node config plus a simulated
weather sensor. Add the config for the driver under test there.

## Committing driver work

A driver change is two commits: one inside `include/osh-addons` (pushed to osh-addons), then one
here that records the new submodule commit.

```sh
cd include/osh-addons
git checkout -b my-driver
git commit -am "..." && git push -u origin my-driver

cd ../..
git add include/osh-addons
git commit -m "Update osh-addons"
```

To move both submodules to the tip of their tracked branch (`master`):

```sh
git submodule update --remote
```
