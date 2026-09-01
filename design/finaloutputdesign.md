# Final Output Files

So we need to do some cleanup still. It'd be nice if we could create a final output version of the source that is:

- Has rewritten and clarified comments from the original source for MasterDOS where appropriate and where they add to the explanations we have here. That means reading them from the commentary there, not just carrying them over line-by-line in an automated fashion.
- With temporary notes (e.g. like the section marked "WITHDRAWN" which are only relevant to you and me)
- With pedagogical explanations of the source code and what it is doing for each routine.
- With zero magic numbers in the opcodes wherever possible. 

It should be a separate section so that you can keep your earlier conclusions and speculations as working copies, and so that the final output is an opinionated explanation of the source code made for easy-reading for a working professional who is familiar with z80, but not necessarily the machine or the architecture.

We'll also refactor the file tree at some point, but for now, the output should go into clean/, and should contain the post-install file (as postinstall-syspage.asm), masterbasic.asm and masterdos.asm.,
