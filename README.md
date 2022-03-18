## Retrieve project files

As of today, you need to retrieve the files of the project locally to create a docker image of the current version.

`git clone https://github.com/FatimaAfilala/ExcelProject.git`

## Create Docker container & run it

Once you have retrieved the files, place yourself in the folder "/ExcelProject" :

`cd ExcelProject`

Now, you can create a docker image containing FARC run:

`docker build -t farc:latest -t farc:1.0.1 .`

Replace 1.0.1 with the current version.

Then to run the created container locally with docker run:

`docker run -it -d -p 9000:8080 farc:latest`

You can replace 9000 with any desired port.
This will start a local version FARC, which can be visited at http://localhost:9000/.

## Development guide

The CARA repository makes use of Git's Large File Storage (LFS) feature.
You will need a working installation of git-lfs in order to run CARA in development mode.
See https://git-lfs.github.com/ for installation instructions.

### Installing CARA in editable mode

```
git lfs pull   # Fetch the data from LFS
pip install -e .   # At the root of the repository
```

### Running the COVID calculator app in development mode

```
python -m cara.apps.calculator
```

To run with the CERN theme:

```
python -m cara.apps.calculator --theme=cara/apps/templates/cern
```

To run the calculator on a different URL path:

```
python -m cara.apps.calculator --prefix=/mycalc
```
