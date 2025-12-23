## Release procedure
- Merge all to-be-included features into `main`
- Bump version by editing `src/mf/version.py`
- Tag the latest commit on `main` with `v<major><minor><patch>` and push it
- Create Github release from the new tag
- Publish to test.pypi.org
    ```
    just pypi-test <version> <token>
    ```
    This will delete build artifacts from previous builds, build `<version>`, then test-publish.
- Check metadata of the new release on [test.pypi.org/project/mediafinder](https://test.pypi.org/project/mediafinder/)
- Run tests against the test publish
    ```
    just pypi-verify <version>
    ```
- If everything works, publish to pypi proper
    ```
    just pypi-production <version> <token>
    ```
    This will delete build artifacts from previous builds, build `<version>`, then publish.
