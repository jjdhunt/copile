copile_from_specification = '''Given a python function prototype and a docstring,  write an implementation.
Add type hints to the function prototype if any are missing.
If the docstring is not in Google style, rewrite it in Google style.
If any modules need to be imported, import them above the function implementation. Don't forget to import types.
Return only one function. Define any needed helper functions inside the main function.
Return only a code block with no other discussion and no examples.
'''

assess_specification = '''Given a python function and a docstring, determine if the function behavior is well specified.
If the described behavior of the function is unclear, ambiguous, or nonsensical, reply with just: 'UNCLEAR: <explanation of what is unclear>'.
If you could, in good faith, figure out what is intended, then reply with just 'CLEAR'.'''

recopile_from_specification = '''Given a python function and a docstring, ensure that the function implementation does exactly what is described by the prototype and docstring. Don't change anything in the implementation except what must be changed to match the description, and the corresponding code comments.
If the docstring is not in Google style, rewrite it in Google style.
If any modules need to be imported, import them above the function implementation.
Return only a code block with no other discussion.'''

check_for_safety_issues = '''Given a python function, you must review it for the following issues and reply with a comma-separated list of the identified issues:
FILE_ACCESS: The code opens or accesses a file.
FILE_DELETION: The code deletes a file.
FILE_WRITE: The code creates or writes to a file.
NON_TERMINATING: The code contains an non-terminating process such as an infinite loop.
CODE_EVAL: The code tries to evaluate source code.
SYSTEM_CALL: The code makes a system call or otherwise tries to run any external software.
GENERALLY_UNSAFE: The code tries to do anything else that might be deemed unsafe.
If none of these issues are present in the code, reply with just NONE.
'''