---
description: Analyze this codebase with sddgrade advise and help the user adopt Spec-Driven Development.
---

# sddgrade — advise on SDD adoption

Help the user adopt Spec-Driven Development (Spec-Kit or OpenSpec) in this codebase.

## Steps

1. Run `sddgrade advise` from the repository root and read its recommendations.
2. Walk the user through them: what the scan found, which SDD toolchain fits, and
   the concrete first steps it suggests.
3. Offer to carry out the recommendations the user wants — e.g. drafting an initial
   `spec.md` for an existing feature, or setting up the Spec-Kit / OpenSpec
   directory layout.
4. Once artifacts exist, point at the rest of the family: `/sddgrade.judge` to
   judge them, `/sddgrade.review` for the scored report, `/sddgrade.fix` to fix the
   top findings.
