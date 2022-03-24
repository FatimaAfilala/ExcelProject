## Retrieve project files

As of today, you need to retrieve the files of the project locally to create a docker image of the current version.

`git clone https://github.com/FatimaAfilala/ExcelProject.git`

## Create Docker container & run it

Once you have retrieved the files (with git clone), place yourself in the folder "/ExcelProject" :

`cd ExcelProject`

Pull the large file with git-lfs:

`git lfs pull`

Now, you can create a docker image containing FARC run:

`docker build -t farc:latest -t farc:1.0.1 .`

Replace 1.0.1 with the current version.

Then to run the created container locally with docker run:

`docker run -d -p 9000:8080 farc:latest`

You can replace 9000 with any desired port.
This will start a local version FARC, which can be visited at http://localhost:9000/.

## Development guide

The CARA repository makes use of Git's Large File Storage (LFS) feature.
You will need a working installation of git-lfs in order to run CARA in development mode.
See https://git-lfs.github.com/ for installation instructions.

### Installing CARA in editable mode (DEV)

## Install git and python 

You might wanna use a virtual environnement before installing dependencies.

Git :    https://git-scm.com/downloads
Python : https://www.python.org/downloads/
Pip :    https://www.liquidweb.com/kb/install-pip-windows/

## Retrieve project files and install dependencies

```
git lfs pull   # Fetch the data from LFS
pip install -e .   # At the root of the repository
```

### Running the COVID calculator app in development mode (DEV)

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
