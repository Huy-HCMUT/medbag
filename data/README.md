# data/

Everything here except this file, `test_samples/` and `manifest.json` is ignored by git.
Download the test photos from Google Drive (`2 Data/`) into `test_set/`.

- `manifest.json`: every test situation (fill check, pre-dose check, dose check), its photo and the expected result (committed). See WBS 2.4.
- `test_set/fill/`, `test_set/pre_dose/`, `test_set/dose/`: the photos named in `manifest.json` (from Drive, not committed)
- `test_samples/label.jpg`, `test_samples/tray.jpg`: one sample photo each, used by the agreement tests (committed)
- `medbag.db`, `photos/`: created by the server at run time
