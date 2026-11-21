<!-- Title: [WBS number] what you did, e.g. [4.1] rectify with ArUco markers -->

**WBS item:**
**What changed:**

**Checklist**
- [ ] `MEDBAG_IMPL=<my package> uv run pytest packages/medbag_common/tests` passes (agreement test)
- [ ] `uv run pytest` passes (all pieces still run together)
- [ ] Function names and parameters are unchanged (or Huy agreed to the change)
- [ ] No `.env`, photos, datasets or `*.pt` files in this PR
- [ ] Libraries added with `uv add --package <my package> ...`, and `uv.lock` is included
