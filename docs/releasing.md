# Releasing

## 1. Update version

Update all of these together:

- `memory_post.py` → `APP_VERSION`
- `pyproject.toml` → `[project].version`
- `packaging/version_info.txt`
- `CHANGELOG.md`
- release notes file

## 2. Run tests

```powershell
pip install -r requirements-dev.txt
pytest
```

## 3. Rebuild exe

```powershell
.\build_exe.bat
```

Expected output:

```text
dist/MemoryPost.exe
```

## 4. Run executable selftest

```powershell
.\dist\MemoryPost.exe --selftest-full .\selftest-out
```

Check that `selftest.log` ends with `SELFTEST_OK`.

## 5. Commit and tag

```powershell
git add .
git commit -m "Release v1.1.0"
git tag v1.1.0
git push origin main
git push origin v1.1.0
```

The GitHub Actions release workflow will build the exe and attach it to the GitHub release.

## 6. Manual release option

If the workflow is unavailable:

1. Open GitHub → Releases → Draft a new release.
2. Choose the `v1.1.0` tag.
3. Use `RELEASE_NOTES_v1.1.0.md` as the description.
4. Upload `dist/MemoryPost.exe`.
5. Publish.

## 7. Checksums

For extra transparency, provide a SHA-256 checksum in the release notes or a separate `.sha256` file.

```powershell
Get-FileHash .\dist\MemoryPost.exe -Algorithm SHA256
```
