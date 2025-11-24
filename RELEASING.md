## Release procedure
- Merge all to-be-included features into `main`
- Bump version by editing `src/mf/version.py`
- Tag the latest commit on `main` with `v<major><minor><patch>` and push it
- Create Github release from the new tag
- Build the package
    ```
    uv build
    ```
- Publish to test.pypi.org
    ```
    uv publish --publish-url https://test.pypi.org/legacy/ --token <token>
    ```
- Check metadata of the new release on [test.pypi.org/project/mediafinder](https://test.pypi.org/project/mediafinder/)
- Run tests against the test publish
    ```
    uvx --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --index-strategy unsafe-best-match --with "jmespath<99.99.99, mediafinder, pytest, pytest-cov" pytest --no-cov tests
    ```
    Note: the pinning of `jmespath<99.99.99` is necessary because one of `mediafinder`'s direct dependencies depends on it and it has a bogus version `99.99.99` on test.pypi.org which can't be installed.
- If everything works, publish to pypi proper
    ```
    uv publish --token <token>
    ```
