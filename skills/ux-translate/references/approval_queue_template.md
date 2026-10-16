# Approval queue template

`approval-queue.md` lies in the brief's folder and holds the keys whose text waits for the team's
approval in ux-approval, plus one line about the artifact. It is not part of the brief: translators
and reviewers never get it. The first writer creates it: Add key, Translate or Review with its
first row, ux-approval with its `Approval:` line and an empty table. A key approved by its task or
design never enters it.

- **`Approval:`** — written by ux-approval after each publication (`open`; Finalize → `final`);
  Apply approved sets `applied`. No line → no artifact yet.
- **Rows** — added by Add key, Translate and Review by the rules in `SKILL.md`; removed by Apply
  approved once the export approves the key.

```markdown
# Approval queue

Approval: <artifact url>, round <n>, <open | final | applied>

| key | date |
|---|---|
```
