# THIRD_PARTY_NOTICES — `_native/src/`

Two source files in this directory are **borrowed from the upstream
[RemCTL](https://github.com/viticci/remctl) project under the MIT License**.
They are vendored verbatim (modulo a small file-header comment block and a
`--ping` argv shortcut for `verify_setup.py`, both clearly marked inline) so
the upstream maintainers' work is preserved with attribution.

## File-by-file mapping

| Upstream file (RemCTL) | Local path |
| --- | --- |
| `remctl-bridge.swift` | `src/mcp_apple_reminders/_native/src/rem_eventkit.swift` |
| `remctl-private.m` | `src/mcp_apple_reminders/_native/src/rem_reminderkit.m` |

## Upstream pin

- Repository: <https://github.com/viticci/remctl>
- Commit: `baaa57b922b6379989cb2cc04f54461faefb1496`
- Tag / release: RemCTL 1.0.3 (2026-05-27)

When re-syncing from upstream, replace both files, re-apply the inline
attribution header block at the top of each, and re-apply the `--ping`
argv shortcut documented in the header.

## Local modifications

The `remctl-bridge.swift` → `rem_eventkit.swift` file has exactly two local
modifications:

1. **File-header comment block** at the very top. Documents the borrow +
   upstream pin + local-modification list. No behavioral effect.
2. **`--ping` CLI shortcut** at the very start of `main`. Emits
   `{"status":"ok","helper":"rem_eventkit"}` to stdout and exits 0.

The `remctl-private.m` → `rem_reminderkit.m` file has the same two mods
plus **two new actions and one private-selector declaration added by S5.1
(ADR 0001 — list-group support)**:

3. New entry in the allowed-action set: `create_group`.
4. New entry in the allowed-action set: `move_list_to_group`.
5. Interface declaration on `REMListChangeItem` for the previously-undeclared
   private selectors `setIsGroup:` and `setParentListID:` (both gated by
   `respondsToSelector:` at call sites). These selectors are reverse-engineered
   from the SQLite schema (`ZISGROUP` + `ZPARENTLIST` columns) and verified
   live on macOS 26.1.
6. Action handler blocks for `create_group` (calls `setIsGroup:YES` on a
   new list change item) and `move_list_to_group` (calls `setParentListID:`
   with the group's `REMObjectID`, or the account's for the detach case).

No other lines have been touched in either file; the upstream JSON-over-stdio
dispatch logic is preserved verbatim around these additions.

## Verbatim MIT License (from upstream `LICENSE`)

```
MIT License

Copyright (c) 2026 RemCTL contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ReminderKit private framework

`rem_reminderkit.m` links against `/System/Library/PrivateFrameworks/
ReminderKit.framework` — an undocumented Apple framework. This is the
**only** path to subtask / flagged-by-API / section / tag writes that the
public EventKit framework does not expose. Pierce explicitly accepted the
private-API risk in spec 002 design.md; if a future macOS release renames
or removes the symbols this helper relies on, the tools that depend on it
degrade — the SQLite reader (Slice 1.0) and the Swift EventKit helper
(`rem_eventkit`) keep working.
