## Create Docker container

To create a docker image containing FARC run:

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

### Running the CARA Expert-App app in development mode

```
voila cara/apps/expert/cara.ipynb --port=8080
```

Then visit http://localhost:8080.

### Running the tests

```
pip install -e .[test]
pytest ./cara
```

### Building the whole environment for local development

**Simulate the docker build that takes place on openshift with:**

```
s2i build file://$(pwd) --copy --keep-symlinks --context-dir ./app-config/nginx/ centos/nginx-112-centos7 cara-nginx-app
docker build . -f ./app-config/cara-webservice/Dockerfile -t cara-webservice
docker build ./app-config/auth-service -t auth-service
```

Get the client secret from the CERN Application portal for the `cara-test` app. See [CERN-SSO-integration](#CERN-SSO-integration) for more info.

```
read CLIENT_SECRET
```

Define some env vars (copy/paste):

```
export COOKIE_SECRET=$(openssl rand -hex 50)
export OIDC_SERVER=https://auth.cern.ch/auth
export OIDC_REALM=CERN
export CLIENT_ID=cara-test
export CLIENT_SECRET
```

Run docker-compose:

```
cd app-config
CURRENT_UID=$(id -u):$(id -g) docker-compose up
```

Then visit http://localhost:8080/.

### Setting up the application on openshift

The https://cern.ch/cara application is running on CERN's OpenShift platform. In order to set it up for the first time, we followed the documentation at https://cern.service-now.com/service-portal?id=kb_article&n=KB0004498. In particular we:

-   Added the OpenShift application deploy key to the GitLab repository
-   Created a Python 3.6 (the highest possible at the time of writing) application in OpenShift
-   Configured a generic webhook on OpenShift, and call that from the CI of the GitLab repository

### Updating the test-cara.web.cern.ch instance

We have a replica of https://cara.web.cern.ch running on http://test-cara.web.cern.ch. Its purpose is to simulate what will happen when
a feature is merged. To push your changes to test-cara, simply push your branch to `live/test-cara` and the CI pipeline will trigger the
deployment. To push to this branch, there is a good chance that you will need to force push - you should always force push with care and
understanding why you are doing it. Syntactically, it will look something like (assuming that you have "upstream" as your remote name,
but it may be origin if you haven't configured it differently):

    git push --force upstream name-of-local-branch:live/test-cara

## OpenShift templates

### First setup

First, get the [oc](https://docs.okd.io/3.11/cli_reference/get_started_cli.html) client and then login:

```console
$ oc login https://api.paas.okd.cern.ch
```

Then, switch to the project that you want to update:

```console
$ oc project test-cara
```

If you need to create the application in a new project, run:

```console
$ cd app-config/openshift

$ oc process -f routes.yaml --param HOST='test-cara.web.cern.ch' | oc create -f -
$ oc process -f configmap.yaml | oc create -f -
$ oc process -f services.yaml | oc create -f -
$ oc process -f imagestreams.yaml | oc create -f -
$ oc process -f buildconfig.yaml --param GIT_BRANCH='live/test-cara' | oc create -f -
$ oc process -f deploymentconfig.yaml --param PROJECT_NAME='test-cara'  | oc create -f -
```

Create a new service account in OpenShift to use GitLab container registry:

```console
$ oc project test-cara

$ oc create serviceaccount gitlabci-deployer
serviceaccount "gitlabci-deployer" created

$ oc policy add-role-to-user registry-editor -z gitlabci-deployer

# We will refer to the output of this command as `test-token`
$ oc serviceaccounts get-token gitlabci-deployer
<...test-token...>
```

Add the token to GitLab to allow GitLab to access OpenShift and define/change image stream tags. Go to `Settings` -> `CI / CD` -> `Variables` -> click on `Expand` button and create the variable `OPENSHIFT_CARA_TEST_DEPLOY_TOKEN`: insert the token `<...test-token...>`.

Then, create the webhook secret to be able to trigger automatic builds from GitLab.

Create and store the secret. Copy the secret above and add it to the GitLab project under `CI /CD` -> `Variables` with the name `OPENSHIFT_CARA_TEST_WEBHOOK_SECRET`.

```console
$ WEBHOOKSECRET=$(openssl rand -hex 50)
$ oc create secret generic \
  --from-literal="WebHookSecretKey=$WEBHOOKSECRET" \
  gitlab-cara-webhook-secret
```

For CI usage, we also suggest creating a service account:

```console
oc create sa gitlab-config-checker
```

Under `Resources` -> `Membership` enable the `View` role for this new service account.

To get this new user's authentication token go to `Resources` -> `Secrets` and locate the token in the newly
created secret associated with the user (in this case `gitlab-config-checker-token-XXXX`).

### CERN SSO integration

The SSO integration uses OpenID credentials configured in [CERN Applications portal](https://application-portal.web.cern.ch/).
How to configure the application:

-   Application Identifier: `cara-test`
-   Homepage: `https://test-cara.web.cern.ch`
-   Administrators: `cara-dev`
-   SSO Registration:
    -   Protocol: `OpenID (OIDC)`
    -   Redirect URI: `https://test-cara.web.cern.ch/auth/authorize`
    -   Leave unchecked all the other checkboxes
-   Define new roles:
    -   Name: `CERN Users`
        -   Role Identifier: `external-users`
        -   Leave unchecked checkboxes
        -   Minimum Level Of Assurance: `CERN (highest)`
        -   Assign role to groups: `cern-accounts-primary` e-group
    -   Name: `External accounts`
        -   Role Identifier: `admin`
        -   Leave unchecked checkboxes
        -   Minimum Level Of Assurance: `Any (no restrictions)`
        -   Assign role to groups: `cara-app-external-access` e-group
    -   Name: `Allowed users`
        -   Role Identifier: `allowed-users`
        -   Check `This role is required to access my application`
        -   Minimum Level Of Assurance:`Any (no restrictions)`
        -   Assign role to groups: `cern-accounts-primary` and `cara-app-external-access` e-groups

Copy the client id and client secret and use it below.

```console
$ COOKIE_SECRET=$(openssl rand -hex 50)
$ oc create secret generic \
  --from-literal="CLIENT_ID=$CLIENT_ID" \
  --from-literal="CLIENT_SECRET=$CLIENT_SECRET" \
  --from-literal="COOKIE_SECRET=$COOKIE_SECRET" \
  auth-service-secrets
```

## Update configuration

If you need to **update** existing configuration, then modify this repository and after having logged in, run:

```console
$ cd app-config/openshift


$ oc process -f configmap.yaml | oc replace -f -
$ oc process -f services.yaml | oc replace -f -
$ oc process -f routes.yaml --param HOST='test-cara.web.cern.ch' | oc replace -f -
$ oc process -f imagestreams.yaml | oc replace -f -
$ oc process -f buildconfig.yaml --param GIT_BRANCH='live/test-cara' | oc replace -f -
$ oc process -f deploymentconfig.yaml --param PROJECT_NAME='test-cara' | oc replace -f -
```

Be aware that if you change/replace the **route** of the PROD instance,
it will lose the annotation to be exposed outside CERN (not committed in this repo).
