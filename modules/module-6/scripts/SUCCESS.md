# What counts as success for invoice-reader

Written before any code, on purpose. Replace this with your own agent's definition.

**A run is a success when it finishes with an answer that has both required fields, and
both pass validation:**

- `amount` is present, is a number, and is between $0.01 and $50,000 (the largest invoice
  finance-ops has ever approved is $38,200; anything above $50,000 is a misread, not an
  invoice);
- `vendor` is present and is not empty.

**Everything else is a failure**, including runs that finished cleanly without an error.
A run that was capped, looped, hit the step limit, was interrupted, or ran out of retries is
a failure too. Its cost still goes on the top of the division.

**Why this definition, and not another one:**

- *"It did not crash"* is too generous: `samples/incomplete.json` finishes cleanly and
  produces nothing finance can use.
- *"A human accepted it"* is the true one, but it arrives days later and cannot be checked
  a hundred times a day. It is what this definition gets audited against once a month.
- *"It passed a check"* is the one we can run on every run, the moment it ends. This is it.

**The test for this file:** could a colleague apply it to ten runs and get the same answers
you would? If not, it is not specific enough yet.
